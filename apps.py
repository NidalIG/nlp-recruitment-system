# apps.py - Backend Flask principal corrigé avec Auth
import os
import json
import tempfile
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
import google.generativeai as genai
from models.result import create_result

from typing import List, Dict, Any

# Imports de vos modules existants
from quiz_module import QuizGenerator, QuizEvaluator, Quiz, QuizQuestion
from cv_parsing.extractors import extract_text
from cv_parsing.gemini_parser import parse_cv_with_gemini
from cv_parsing.job_parsing import parse_job
from cv_job_matching import CVJobEmbeddingSimilarity

app = Flask(__name__)
CORS(app)

# -------------------- CONFIG --------------------
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key')

# MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri)
db = client['jobmatch']
users_collection = db['users']

bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# -------------------- GEMINI --------------------
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Instance globale du calculateur de similarité
try:
    similarity_calculator = CVJobEmbeddingSimilarity(model_type="sentence_transformer")
    print("✅ SentenceTransformer chargé avec succès")
except Exception as e:
    print(f"❌ Erreur chargement modèle: {e}")
    similarity_calculator = None

try:
    quiz_generator = QuizGenerator(model)
    print("✅ Générateur de quiz initialisé avec succès")
except Exception as e:
    print(f"❌ Erreur initialisation générateur de quiz: {e}")
    quiz_generator = None

# -------------------- HELPERS --------------------
def _first_non_empty(*vals):
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def _top(items: List[str], k=8):
    return [s for s in items if isinstance(s, str) and s.strip()][:k]

def summarize_cv_for_card(cv: Dict[str, Any]) -> Dict[str, Any]:
    # cv est déjà un dict structuré (retour de parse_cv_with_gemini)
    name = cv.get("name") or cv.get("full_name") or "Candidat"
    skills = cv.get("skills", [])
    exp = cv.get("experience", []) or []
    edu = cv.get("education", []) or []
    langs = cv.get("languages", []) or []

    # Titre court = dernier poste si dispo
    last_role = None
    last_company = None
    if exp and isinstance(exp, list):
        last = exp[0]  # on suppose l’expérience la plus récente en premier
        last_role = _first_non_empty(last.get("job_title"), last.get("title"), last.get("role"))
        last_company = _first_non_empty(last.get("company"), last.get("company_name"), last.get("employer"))

    highest_degree = None
    if edu and isinstance(edu, list):
        e0 = edu[0]
        highest_degree = _first_non_empty(e0.get("degree"), e0.get("diploma"), e0.get("title"))

    bullets = []
    if last_role or last_company:
        bullets.append(f"Dernière expérience : {last_role or 'Poste'} @ {last_company or 'Entreprise'}")
    if highest_degree:
        bullets.append(f"Formation principale : {highest_degree}")
    if langs:
        bullets.append("Langues : " + ", ".join(_top([str(l) for l in langs], 4)))
    if skills:
        bullets.append("Compétences clés : " + ", ".join(_top([str(s) for s in skills], 6)))

    return {
        "type": "cv",
        "title": name,
        "subtitle": last_role or "Profil du candidat",
        "chips": _top([str(s) for s in skills], 8),
        "bullets": bullets,
        "updatedAt": datetime.utcnow().isoformat() + "Z"
    }

def summarize_job_for_card(job: Dict[str, Any]) -> Dict[str, Any]:
    title = job.get("title") or "Offre"
    company = _first_non_empty(job.get("company"), job.get("employer"), job.get("organization"))
    location = _first_non_empty(job.get("location"), job.get("city"))
    required_skills = job.get("required_skills", []) or []
    responsibilities = job.get("responsibilities", []) or job.get("missions", []) or []
    requirements = job.get("requirements", []) or []

    bullets = []
    if company:
        bullets.append(f"Entreprise : {company}")
    if location:
        bullets.append(f"Localisation : {location}")
    if responsibilities:
        bullets.append("Responsabilités : " + ", ".join(_top([str(r) for r in responsibilities], 3)))
    if requirements:
        bullets.append("Pré-requis : " + ", ".join(_top([str(r) for r in requirements], 3)))
    if required_skills:
        bullets.append("Compétences demandées : " + ", ".join(_top([str(s) for s in required_skills], 6)))

    return {
        "type": "job",
        "title": title,
        "subtitle": company or "Job description",
        "chips": _top([str(s) for s in required_skills], 8),
        "bullets": bullets,
        "updatedAt": datetime.utcnow().isoformat() + "Z"
    }

def build_profile_card(user_doc: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, Any]:
    full_name = " ".join(filter(None, [user_doc.get("firstName"), user_doc.get("lastName")])).strip() or "Utilisateur"
    email = user_doc.get("email", "")
    created = user_doc.get("createdAt") or ""
    bullets = [
        f"Email : {email}",
        f"Compte créé le : {created[:10]}" if isinstance(created, str) else "Compte créé : -",
        f"Historique : {stats.get('cv_count',0)} CV, {stats.get('job_count',0)} offres, {stats.get('quiz_count',0)} quiz"
    ]
    return {
        "type": "profile",
        "title": full_name,
        "subtitle": "Profil utilisateur",
        "chips": ["Inscrit", "Authentifié"],
        "bullets": bullets,
        "updatedAt": datetime.utcnow().isoformat() + "Z"
    }


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_result_to_db(user_id, result_type, data, meta=None, refs=None):
    """Helper pour sauvegarder automatiquement les résultats"""
    try:
        result = create_result(user_id, result_type, data, meta, refs)
        db.results.insert_one(result)
        print(f"✅ Résultat {result_type} sauvegardé pour user {user_id}")
    except Exception as e:
        print(f"❌ Erreur sauvegarde résultat: {e}")

def generate_feedback(percentage: float, detailed_results: list) -> dict:
    """Petit helper de feedback pour l'évaluation du quiz (évite un NameError)."""
    if percentage >= 80:
        return {"level": "Excellent", "message": "Félicitations ! Vous maîtrisez très bien le sujet.", "color": "green"}
    if percentage >= 60:
        return {"level": "Bien", "message": "Bon travail ! Quelques points à revoir mais vous êtes sur la bonne voie.", "color": "blue"}
    if percentage >= 40:
        return {"level": "Moyen", "message": "Il y a des lacunes à combler. Continuez à étudier !", "color": "orange"}
    return {"level": "À améliorer", "message": "Il faut revoir les bases. Ne vous découragez pas !", "color": "red"}

# -------------------- AUTH --------------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    email = data.get('email')
    password = data.get('password')
    firstName = data.get('firstName')
    lastName = data.get('lastName')

    if not email or not password:
        return jsonify({'success': False, 'error': 'Email et mot de passe requis'}), 400

    if users_collection.find_one({'email': email}):
        return jsonify({'success': False, 'error': 'Email déjà utilisé'}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    user = {
        'email': email,
        'password': pw_hash,
        'firstName': firstName,
        'lastName': lastName,
        'createdAt': datetime.now(timezone.utc).isoformat()
    }
    result = users_collection.insert_one(user)

    # Génération du token JWT
    access_token = create_access_token(
        identity=str(result.inserted_id),
        expires_delta=timedelta(hours=1)
    )

    return jsonify({
        'success': True,
        'message': 'Utilisateur créé avec succès',
        'accessToken': access_token,
        'user': {
            'email': email,
            'firstName': firstName,
            'lastName': lastName
        }
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    email = data.get('email')
    password = data.get('password')

    user = users_collection.find_one({'email': email})
    if not user or not bcrypt.check_password_hash(user['password'], password):
        return jsonify({'success': False, 'error': 'Identifiants invalides'}), 401
    
    access_token = create_access_token(
        identity=str(user['_id']),
        expires_delta=timedelta(hours=1)
    )
    
    return jsonify({
        'success': True,
        'accessToken': access_token,
        'user': {
            'email': user['email'],
            'firstName': user.get('firstName'),
            'lastName': user.get('lastName')
        }
    })

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        return jsonify({'success': False, 'error': 'ID utilisateur invalide'}), 400
    
    user = users_collection.find_one({'_id': obj_id}, {'password': 0})
    if not user:
        return jsonify({'success': False, 'error': 'Utilisateur introuvable'}), 404
    
    user['_id'] = str(user['_id'])
    return jsonify({'success': True, 'user': user})

@app.route('/api/results', methods=['POST'])
@jwt_required()
def save_result():
    """Sauvegarder un résultat (CV parsing, job parsing, quiz, matching)"""
    data = request.get_json()
    if not data or "type" not in data or "data" not in data:
        return jsonify({"error": "type & data requis"}), 400

    user_id = get_jwt_identity()
    result = create_result(user_id, data["type"], data["data"], data.get("meta"), data.get("refs"))
    db.results.insert_one(result)

    result["_id"] = str(result["_id"])
    result["user"] = str(result["user"])
    return jsonify(result), 201


@app.route('/api/results', methods=['GET'])
@jwt_required()
def get_results():
    """Récupérer la liste des résultats de l'utilisateur (avec pagination)"""
    user_id = get_jwt_identity()
    type_filter = request.args.get("type")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))

    query = {"user": ObjectId(user_id)}
    if type_filter:
        query["type"] = type_filter

    cursor = db.results.find(query).sort("createdAt", -1).skip((page-1)*limit).limit(limit)
    results = []
    for r in cursor:
        r["_id"] = str(r["_id"])
        r["user"] = str(r["user"])
        results.append(r)

    return jsonify(results), 200

@app.route('/api/assistant/cards', methods=['GET'])
@jwt_required()
def get_assistant_cards():
    """
    Retourne 3 cartes:
      - profile: infos de l'utilisateur (users_collection)
      - cv: résumé du dernier CV parsé (db.results type='cv')
      - job: résumé de la dernière job_description parsée (db.results type='job')
    + Fallback: si pas de 'job' (ou 'cv'), chercher dans le dernier 'matching'
    """
    try:
        user_id = get_jwt_identity()
        obj_id = ObjectId(user_id)

        # Profil
        user = users_collection.find_one({'_id': obj_id}, {'password': 0}) or {}

        # Dernier CV parsé
        latest_cv_result = db.results.find_one(
            {"user": obj_id, "type": "cv"},
            sort=[("createdAt", -1)]
        )
        cv_card = None
        if latest_cv_result and latest_cv_result.get("data"):
            cv_data = latest_cv_result["data"]
            if isinstance(cv_data, dict) and "parsed_cv" in cv_data:
                cv_data = cv_data["parsed_cv"]
            cv_card = summarize_cv_for_card(cv_data)

        # Dernière offre parsée
        latest_job_result = db.results.find_one(
            {"user": obj_id, "type": "job"},
            sort=[("createdAt", -1)]
        )
        job_card = None
        if latest_job_result and latest_job_result.get("data"):
            job_card = summarize_job_for_card(latest_job_result["data"])

        # 🔁 Fallback depuis le dernier MATCHING si besoin
        if not job_card or not cv_card:
            latest_match = db.results.find_one(
                {"user": obj_id, "type": "matching"},
                sort=[("createdAt", -1)]
            )
            if latest_match:
                mdata = latest_match.get("data", {})
                if not job_card and isinstance(mdata.get("parsed_job"), dict):
                    job_card = summarize_job_for_card(mdata["parsed_job"])
                if not cv_card and isinstance(mdata.get("parsed_cv"), dict):
                    cv_card = summarize_cv_for_card(mdata["parsed_cv"])

        # petites stats
        cv_count = db.results.count_documents({"user": obj_id, "type": "cv"})
        job_count = db.results.count_documents({"user": obj_id, "type": "job"})
        quiz_count = db.results.count_documents({"user": obj_id, "type": {"$in": ["quiz", "quiz_evaluation"]}})

        profile_card = build_profile_card(user, {
            "cv_count": cv_count, "job_count": job_count, "quiz_count": quiz_count
        })

        return jsonify({
            "success": True,
            "cards": {
                "profile": profile_card,
                "cv": cv_card,
                "job": job_card
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"Erreur assistant: {str(e)}"}), 500

# -------------------- CHAT GEMINI --------------------
@app.route('/api/chat', methods=['POST'])
@jwt_required(optional=True)
def chat_with_gemini():
    """
    Chat général branché sur Gemini, avec contexte CV/JD si l'utilisateur est authentifié.
    Le front envoie: { "messages": [ {role, content}, ... ] }
    """
    try:
        payload = request.get_json() or {}
        incoming = payload.get("messages", [])

        # 1) System prompt (sinon défaut)
        sys = next((m.get("content") for m in incoming if m.get("role") == "system"), None)
        system_instruction = sys or (
            "Tu es un assistant utile spécialisé en recrutement. "
            "Réponds en FRANÇAIS, de façon claire et concise. "
            "Si la question concerne le candidat, appuie-toi sur le CV et la Job Description si disponibles."
        )

        # 2) Contexte utilisateur (CV/JD)
        user_id = get_jwt_identity()
        ctx_lines = []
        if user_id:
            obj_id = ObjectId(user_id)
            latest_cv = db.results.find_one({"user": obj_id, "type": "cv"}, sort=[("createdAt", -1)])
            latest_job = db.results.find_one({"user": obj_id, "type": "job"}, sort=[("createdAt", -1)])

            if latest_cv and latest_cv.get("data"):
                cv_data = latest_cv["data"].get("parsed_cv", latest_cv["data"])
                cv_card = summarize_cv_for_card(cv_data)
                ctx_lines.append(f"[CV] {cv_card['title']} — {cv_card['subtitle']}. " +
                                 " | ".join(cv_card.get("bullets", [])))
            if latest_job and latest_job.get("data"):
                job_card = summarize_job_for_card(latest_job["data"])
                ctx_lines.append(f"[JOB] {job_card['title']} — {job_card['subtitle']}. " +
                                 " | ".join(job_card.get("bullets", [])))

        context_blob = "\n".join(ctx_lines) if ctx_lines else ""

        # 3) Construire l'historique pour Gemini (ignorer 'system'; on l'injecte à part)
        history = []
        for m in incoming:
            role = m.get("role")
            content = m.get("content", "")
            if role == "user":
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                history.append({"role": "model", "parts": [content]})

        # 4) Instancier le modèle avec l’instruction système + contexte
        chat_model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=system_instruction + ("\n\nContexte:\n" + context_blob if context_blob else "")
        )

        resp = chat_model.generate_content(history if history else [{"role": "user", "parts": ["Bonjour"]}])
        text = (resp.text or "").strip() or "(Réponse vide)"

        return jsonify({
            "message": {"role": "assistant", "content": text},
            "success": True
        })
    except Exception as e:
        return jsonify({"error": f"Erreur chat: {str(e)}"}), 500

# -------------------- TES ROUTES EXISTANTES --------------------
@app.route('/', methods=['GET'])
def home():
    """Page d'accueil pour tester le serveur"""
    return jsonify({
        'message': 'Serveur de matching CV actif',
        'status': 'ok',
        'endpoints': ['/api/upload', '/api/parse-cv', '/api/parse-job', '/api/match', '/api/health']
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Vérification de l'état du serveur"""
    return jsonify({
        'status': 'ok',
        'model_available': similarity_calculator is not None and hasattr(similarity_calculator, 'model') and similarity_calculator.model is not None,
        'model_type': similarity_calculator.model_type if similarity_calculator else 'none'
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload et extraction de texte depuis un fichier CV"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Aucun fichier sélectionné'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Type de fichier non supporté'}), 400
        
        # Sauvegarde temporaire
        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(temp_path)
        
        try:
            # Extraction du texte
            extracted_text = extract_text(temp_path)
            
            # Vérification si le texte est vide (PDF scanné)
            warning = ""
            if not extracted_text.strip():
                warning = "Aucun texte détecté. PDF scanné ? Utilisez un PDF texte ou passez par un OCR."
            elif len(extracted_text.strip()) < 50:
                warning = "Texte très court détecté. Vérifiez la qualité du fichier."
            
            return jsonify({
                'text': extracted_text,
                'filename': filename,
                'warning': warning,
                'success': True
            })
        
        except Exception as e:
            return jsonify({'error': f'Erreur d\'extraction: {str(e)}'}), 500
        
        finally:
            # Nettoyage du fichier temporaire
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@app.route('/api/parse-cv', methods=['POST'])
@jwt_required()
def parse_cv():
    """Parse structuré d'un CV avec Gemini"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON manquantes'}), 400
            
        cv_text = data.get('cvText', '').strip()
        
        if not cv_text:
            return jsonify({'error': 'Texte CV manquant'}), 400
        
        # Parsing avec Gemini
        parsed_data = parse_cv_with_gemini(cv_text)
        
        # Conversion string -> dict si nécessaire
        if isinstance(parsed_data, str):
            try:
                parsed_data = json.loads(parsed_data)
            except json.JSONDecodeError:
                return jsonify({'error': 'Erreur de parsing JSON'}), 500
        
        # 🎯 SAUVEGARDE AUTOMATIQUE CV
        user_id = get_jwt_identity()
        save_result_to_db(
            user_id=user_id,
            result_type="cv",
            data=parsed_data,
            meta={
                "source": "gemini_parser",
                "original_text_length": len(cv_text)
            }
        )
        
        return jsonify({
            'parsed_cv': parsed_data,
            'success': True
        })
    
    except Exception as e:
        return jsonify({'error': f'Erreur parsing CV: {str(e)}'}), 500

@app.route('/api/parse-job', methods=['POST'])
@jwt_required()
def parse_job_description():
    """Parse structuré d'une job description"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON manquantes'}), 400
            
        job_text = data.get('jobText', '').strip()
        
        if not job_text:
            return jsonify({'error': 'Texte job description manquant'}), 400
        
        # Parsing de la job description
        parsed_job = parse_job(job_text)
        
        # 🎯 SAUVEGARDE AUTOMATIQUE JOB
        user_id = get_jwt_identity()
        save_result_to_db(
            user_id=user_id,
            result_type="job",
            data=parsed_job,
            meta={
                "source": "job_parser",
                "original_text_length": len(job_text)
            }
        )
        
        return jsonify({
            'parsed_job': parsed_job,
            'success': True
        })
    
    except Exception as e:
        return jsonify({'error': f'Erreur parsing job: {str(e)}'}), 500

@app.route('/api/match', methods=['POST'])
@jwt_required()
def calculate_matching():
    """Calcul du score de matching entre CV et job"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON manquantes'}), 400
            
        cv_text = data.get('cvText', '').strip()
        job_text = data.get('jobText', '').strip()
        
        if not cv_text or not job_text:
            return jsonify({'error': 'CV et job description requis'}), 400
        
        # Vérifier que le calculateur est disponible
        if not similarity_calculator or not hasattr(similarity_calculator, 'model') or similarity_calculator.model is None:
            return jsonify({'error': 'Modèle de similarité non disponible'}), 500
        
        # Parse les deux textes d'abord
        try:
            parsed_cv = parse_cv_with_gemini(cv_text)
            if isinstance(parsed_cv, str):
                parsed_cv = json.loads(parsed_cv)
        except Exception as e:
            return jsonify({'error': f'Erreur parsing CV: {str(e)}'}), 500
        
        # --- parse de la JD ---
        try:
            parsed_job = parse_job(job_text)
        except Exception as e:
            return jsonify({'error': f'Erreur parsing job: {str(e)}'}), 500

        # --- autosave de la JD pour alimenter l’assistant (/api/assistant/cards) ---
        try:
            user_id = get_jwt_identity()
            save_result_to_db(
                user_id=user_id,
                result_type="job",
                data=parsed_job,
                meta={
                    "source": "match_endpoint_autosave",
                    "original_text_length": len(job_text)
                }
            )
        except Exception as e:
            app.logger.warning(f"Autosave job failed: {e}")
                
        # Calcul de similarité avec embedding
        try:
            similarity_result = similarity_calculator.calculate_comprehensive_embedding_similarity(
                parsed_cv, parsed_job
            )
            
            # Analyse des mots-clés manquants
            cv_skills = parsed_cv.get('skills', []) if parsed_cv else []
            job_skills = parsed_job.get('required_skills', []) if parsed_job else []
            
            missing_keywords = []
            if job_skills and cv_skills:
                cv_skills_lower = [skill.lower() for skill in cv_skills]
                missing_keywords = [
                    skill for skill in job_skills 
                    if skill.lower() not in cv_skills_lower
                ]
            
            # Suggestions basées sur le score
            suggestions = []
            overall_score = similarity_result.get('overall_similarity_score', 0)
            
            if overall_score < 40:
                suggestions.append("Votre profil semble peu adapté à ce poste")
            elif overall_score < 55:
                suggestions.append("Ajoutez plus de compétences techniques mentionnées dans l'offre")
            elif overall_score < 70:
                suggestions.append("Mettez en avant votre expérience pertinente")
            else:
                suggestions.append("Excellent match ! Mettez en avant vos points forts")
            
            if missing_keywords:
                suggestions.append(f"Considérez d'acquérir ces compétences: {', '.join(missing_keywords[:3])}")
            
            # Préparer les données de réponse
            matching_data = {
                'score': similarity_result.get('overall_similarity_score', 0),
                'similarity_level': similarity_result.get('similarity_level', 'Calculé'),
                'sectional_scores': similarity_result.get('sectional_scores', {}),
                'skill_analysis': similarity_result.get('skill_analysis', {}),
                'missing_keywords': missing_keywords,
                'suggestions': suggestions,
                'method': f'Embedding similarity ({similarity_result.get("model_used", "sentence_transformer")})',
                'parsed_cv': parsed_cv,
                'parsed_job': parsed_job,
                'success': True
            }
            
            # 🎯 SAUVEGARDE AUTOMATIQUE MATCHING
            save_result_to_db(
                user_id=user_id,
                result_type="matching",
                data=matching_data,
                meta={
                    "model_used": similarity_result.get("model_used", "sentence_transformer"),
                    "cv_text_length": len(cv_text),
                    "job_text_length": len(job_text)
                },
                refs={
                    "cv_skills_count": len(cv_skills),
                    "job_skills_count": len(job_skills),
                    "missing_skills_count": len(missing_keywords)
                }
            )
            
            return jsonify(matching_data)
        
        except Exception as e:
            return jsonify({'error': f'Erreur calcul similarité: {str(e)}'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Erreur matching: {str(e)}'}), 500

@app.route('/api/detailed-report', methods=['POST'])
def generate_detailed_report():
    """Génère un rapport détaillé de matching"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON manquantes'}), 400
            
        cv_text = data.get('cvText', '').strip()
        job_text = data.get('jobText', '').strip()
        
        if not cv_text or not job_text:
            return jsonify({'error': 'CV et job description requis'}), 400
        
        if not similarity_calculator or not hasattr(similarity_calculator, 'model') or similarity_calculator.model is None:
            return jsonify({'error': 'Modèle de similarité non disponible'}), 500
        
        # Parse les données
        parsed_cv = parse_cv_with_gemini(cv_text)
        if isinstance(parsed_cv, str):
            parsed_cv = json.loads(parsed_cv)
        
        parsed_job = parse_job(job_text)
        
        # Génère le rapport détaillé
        report = similarity_calculator.generate_detailed_report(parsed_cv, parsed_job)
        
        return jsonify({
            'report': report,
            'success': True
        })
    
    except Exception as e:
        return jsonify({'error': f'Erreur génération rapport: {str(e)}'}), 500

@app.route('/api/quiz', methods=['POST'])
@jwt_required()
def generate_quiz():
    """Génère un quiz basé sur le profil utilisateur réel (CV parsé) et les compétences matchées (focus_skills)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400
        
        level = data.get('level', 'moyen')
        count = data.get('count', 5)
        user_id = get_jwt_identity()
        
        # Vérification
        if not quiz_generator:
            return jsonify({'error': 'Générateur non disponible'}), 500
        
        # Mapping niveau
        level_map = {
            'facile': 'débutant',
            'moyen': 'intermédiaire', 
            'difficile': 'avancé'
        }
        mapped_level = level_map.get(level, 'intermédiaire')
        
        # Profil utilisateur depuis le CV
        user_profile = get_user_profile_from_cv(user_id)

        # 🔎 Compétences ciblées depuis le DERNIER MATCHING
        focus_skills = []
        latest_match = db.results.find_one(
            {"user": ObjectId(user_id), "type": "matching"},
            sort=[("createdAt", -1)]
        )
        if latest_match:
            sa = latest_match.get("data", {}).get("skill_analysis", {})
            top = sa.get("top_skill_matches", []) or []
            focus_skills = [t.get("job_skill") for t in top if t.get("job_skill")][:5]

        # Génération du quiz (avec tolérance si votre QuizGenerator n'a pas encore 'focus_skills')
        try:
            quiz = quiz_generator.generate_quiz(
                user_profile=user_profile,
                level=mapped_level,
                num_questions=count,
                focus_skills=focus_skills
            )
        except TypeError:
            # Ancienne signature (fallback)
            quiz = quiz_generator.generate_quiz(
                user_profile=user_profile,
                level=mapped_level,
                num_questions=count
            )
        
        if not quiz:
            return jsonify({'error': 'Génération échouée'}), 500
        
        # Format pour le frontend
        questions = []
        for i, q in enumerate(quiz.questions):
            # Nettoyer les options (retirer A), B), etc.)
            clean_choices = []
            for option in q.options:
                if ') ' in option:
                    clean_choices.append(option.split(') ', 1)[1])
                else:
                    clean_choices.append(option)
            
            questions.append({
                'id': i,
                'question': q.question,
                'choices': clean_choices,
                'answerIndex': q.correct_answer,
                'explanation': q.explanation,
                'skillArea': q.skill_area
            })
        
        quiz_data = {
            'success': True,
            'questions': questions,
            'quiz_info': {
                'title': quiz.title,
                'description': quiz.description,
                'estimated_duration': quiz.estimated_duration,
                'level': level,
                'profile_used': user_profile.get('name', 'Utilisateur'),
                'skills_detected': len(user_profile.get('skills', [])),
                'focus_skills': focus_skills
            }
        }
        
        # 🎯 SAUVEGARDE AUTOMATIQUE QUIZ
        save_result_to_db(
            user_id=user_id,
            result_type="quiz",
            data=quiz_data,
            meta={
                "level": level,
                "mapped_level": mapped_level,
                "questions_count": count,
                "generated_questions": len(questions),
                "profile_source": "cv_parsing"
            }
        )
        
        return jsonify(quiz_data)
    
    except Exception as e:
        print(f"❌ Erreur génération quiz: {str(e)}")
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


def get_user_profile_from_cv(user_id):
    """Récupère le profil utilisateur depuis les CV parsés"""
    try:
        # Récupération du dernier CV parsé de l'utilisateur
        latest_cv = db.results.find_one(
            {"user": ObjectId(user_id), "type": "cv"},
            sort=[("createdAt", -1)]
        )
        
        if latest_cv and latest_cv.get('data'):
            cv_data = latest_cv['data']
            
            # Si c'est un CV parsé, extraire les données structurées
            if isinstance(cv_data, dict) and 'parsed_cv' in cv_data:
                cv_parsed = cv_data['parsed_cv']
            else:
                cv_parsed = cv_data
            
            # Construction du profil pour le générateur de quiz
            user_profile = {
                'name': cv_parsed.get('name', 'Candidat'),
                'skills': cv_parsed.get('skills', []),
                'education': cv_parsed.get('education', []),
                'experience': cv_parsed.get('experience', []),
                'languages': cv_parsed.get('languages', []),
                'certifications': cv_parsed.get('certifications', [])
            }
            
            print(f"✅ Profil utilisateur récupéré: {user_profile.get('name')} avec {len(user_profile.get('skills', []))} compétences")
            return user_profile
            
        else:
            print(f"⚠️ Aucun CV trouvé pour l'utilisateur {user_id}, utilisation du profil par défaut")
            # Récupération du profil utilisateur basique depuis la collection users
            user = users_collection.find_one({'_id': ObjectId(user_id)})
            
            return {
                'name': f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() or 'Candidat',
                'skills': ['Développement', 'Programmation', 'Informatique'],
                'education': [{'degree': 'Formation générale'}],
                'experience': [{'title': 'Expérience professionnelle', 'duration': 'Variable'}],
                'languages': ['Français'],
                'certifications': []
            }
            
    except Exception as e:
        print(f"❌ Erreur récupération profil: {str(e)}")
        
        # Profil de fallback en cas d'erreur
        return {
            'name': 'Candidat',
            'skills': ['JavaScript', 'Python', 'HTML', 'CSS', 'React'],
            'education': [{'degree': 'Formation développement'}],
            'experience': [{'title': 'Développeur', 'duration': '2 ans'}],
            'languages': ['Français'],
            'certifications': []
        }


@app.route('/api/quiz/profile-status', methods=['GET'])
@jwt_required()
def get_quiz_profile_status():
    """Retourne des informations sur le profil utilisateur pour les quiz"""
    try:
        user_id = get_jwt_identity()
        
        # Vérifier s'il y a un CV parsé
        latest_cv = db.results.find_one(
            {"user": ObjectId(user_id), "type": "cv"},
            sort=[("createdAt", -1)]
        )
        
        if latest_cv:
            cv_data = latest_cv.get('data', {})
            if isinstance(cv_data, dict) and 'parsed_cv' in cv_data:
                cv_parsed = cv_data['parsed_cv']
            else:
                cv_parsed = cv_data
                
            return jsonify({
                'has_cv': True,
                'profile_name': cv_parsed.get('name', 'Candidat'),
                'skills_count': len(cv_parsed.get('skills', [])),
                'experience_count': len(cv_parsed.get('experience', [])),
                'last_updated': latest_cv.get('createdAt'),
                'recommendation': 'Quiz personnalisé basé sur votre CV'
            })
        else:
            return jsonify({
                'has_cv': False,
                'profile_name': 'Profil générique',
                'skills_count': 5,
                'experience_count': 1,
                'last_updated': None,
                'recommendation': 'Uploadez votre CV pour des quiz personnalisés'
            })
            
    except Exception as e:
        return jsonify({'error': f'Erreur récupération statut: {str(e)}'}), 500

@app.route('/api/quiz/evaluate', methods=['POST'])
@jwt_required()
def evaluate_quiz():
    """Évalue les réponses du quiz avec Gemini"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON manquantes'}), 400

        answers = data.get('answers', {})  # {questionId: selectedIndex}
        questions_data = data.get('questions', [])

        if not questions_data:
            return jsonify({'error': 'Questions manquantes pour l\'évaluation'}), 400

        # 1️⃣ Reconstruire les questions du quiz
        quiz_questions = []
        for q in questions_data:
            question = QuizQuestion(
                question=q['question'],
                options=q['choices'],
                correct_answer=q['answerIndex'],
                explanation=q.get('explanation', ''),
                skill_area=q.get('skillArea', 'Général'),
                difficulty=q.get('difficulty', 'moyen')
            )
            quiz_questions.append(question)

        # 2️⃣ Construire un Quiz temporaire
        quiz = Quiz(
            title="Évaluation Candidat",
            description="Quiz évalué par Gemini",
            level="moyen",
            questions=quiz_questions,
            estimated_duration=len(quiz_questions) * 2
        )

        # 3️⃣ Évaluer avec QuizEvaluator
        evaluator = QuizEvaluator()
        # Note : user_answers doit être {index_question: index_reponse}
        results = evaluator.evaluate_answers(quiz, {i: answers.get(str(q.get('id', i)), -1)
                                                     for i, q in enumerate(questions_data)})

        # 4️⃣ Préparer le retour JSON détaillé
        detailed_results = []
        for i, ua in enumerate(results.user_answers):
            q = quiz.questions[i]
            user_answer_index = ua.selected_option
            user_answer_text = q.options[user_answer_index] if user_answer_index >= 0 else "Aucune réponse"
            detailed_results.append({
                'question_id': i,
                'question': q.question,
                'user_answer': user_answer_text,
                'correct_answer': q.options[q.correct_answer],
                'is_correct': ua.is_correct,
                'explanation': q.explanation,
                'skill_area': q.skill_area
            })

        # 5️⃣ Calcul du feedback basé sur percentage et compétences
        percentage = results.percentage
        feedback = generate_feedback(percentage, detailed_results)

        evaluation_data = {
            'success': True,
            'score': results.score,
            'total': results.total_questions,
            'percentage': round(results.percentage, 1),
            'detailed_results': detailed_results,
            'feedback': feedback
        }
        
        # 🎯 SAUVEGARDE AUTOMATIQUE ÉVALUATION QUIZ
        user_id = get_jwt_identity()
        save_result_to_db(
            user_id=user_id,
            result_type="quiz_evaluation",
            data=evaluation_data,
            meta={
                "questions_count": len(questions_data),
                "answers_provided": len([a for a in answers.values() if a >= 0])
            },
            refs={
                "score": results.score,
                "percentage": results.percentage
            }
        )

        return jsonify(evaluation_data)

    except Exception as e:
        return jsonify({'error': f'Erreur évaluation: {str(e)}'}), 500  

@app.route('/api/users/<id>', methods=['GET'])
@jwt_required()
def get_user(id):
    current_user_id = get_jwt_identity()
    if current_user_id != id:
        return jsonify({"error": "Accès non autorisé"}), 403

    user = users_collection.find_one({"_id": ObjectId(id)}, {"password": 0})
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 404

    user["_id"] = str(user["_id"])
    return jsonify(user)
     

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint non trouvé'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

if __name__ == '__main__':
    print("🚀 Serveur de matching CV démarré")
    print(f"📁 Dossier uploads: {UPLOAD_FOLDER}")
    print(f"🤖 Modèle de similarité: {similarity_calculator.model_type if similarity_calculator else 'Indisponible'}")
    
app.run(
    debug=True,
    host='0.0.0.0',
    port=3001,
    threaded=True
)
