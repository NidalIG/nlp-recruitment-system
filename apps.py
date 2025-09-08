# apps.py
import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

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

# --- Vos modules locaux (gardez vos implémentations existantes) ---
from cv_parsing.extractors import extract_text
from cv_parsing.gemini_parser import parse_cv_with_gemini
from cv_parsing.job_parsing import parse_job
from cv_job_matching import CVJobEmbeddingSimilarity
from quiz_module import QuizGenerator, QuizEvaluator, Quiz, QuizQuestion
from models.result import create_result

# -------------------- CONFIG APP --------------------
app = Flask(__name__)
# CORS pour Vite (5173) + Allow Authorization header
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}
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
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Similarity model
try:
    similarity_calculator = CVJobEmbeddingSimilarity(model_type="sentence_transformer")
    print("✅ SentenceTransformer chargé")
except Exception as e:
    print(f"❌ Erreur modèle similarité: {e}")
    similarity_calculator = None

# Quiz generator
try:
    quiz_generator = QuizGenerator(gemini_model)
    print("✅ Générateur de quiz prêt")
except Exception as e:
    print(f"❌ Erreur générateur quiz: {e}")
    quiz_generator = None

# -------------------- HELPERS GÉNÉRAUX --------------------
def _first_non_empty(*vals):
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def _top(items: List[str], k=8):
    return [s for s in items if isinstance(s, str) and s.strip()][:k]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_result_to_db(user_id, result_type, data, meta=None, refs=None):
    try:
        result = create_result(user_id, result_type, data, meta, refs)
        db.results.insert_one(result)
        print(f"✅ Résultat {result_type} sauvegardé")
    except Exception as e:
        print(f"❌ Erreur save_result: {e}")

def generate_feedback(percentage: float, detailed_results: list) -> dict:
    if percentage >= 80:
        return {"level": "Excellent", "message": "Félicitations ! Vous maîtrisez très bien le sujet.", "color": "green"}
    if percentage >= 60:
        return {"level": "Bien", "message": "Bon travail ! Quelques points à revoir.", "color": "blue"}
    if percentage >= 40:
        return {"level": "Moyen", "message": "Il y a des lacunes à combler.", "color": "orange"}
    return {"level": "À améliorer", "message": "Revoyez les bases, courage !", "color": "red"}

# -------------------- HELPERS CARTES --------------------
def summarize_cv_for_card(cv: Dict[str, Any]) -> Dict[str, Any]:
    name = cv.get("name") or cv.get("full_name") or "Candidat"
    skills = cv.get("skills", []) or []
    exp = cv.get("experience", []) or []
    edu = cv.get("education", []) or []
    langs = cv.get("languages", []) or []

    last_role = last_company = None
    if isinstance(exp, list) and exp:
        last = exp[0]
        last_role = _first_non_empty(last.get("job_title"), last.get("title"), last.get("role"))
        last_company = _first_non_empty(last.get("company"), last.get("company_name"), last.get("employer"))

    highest_degree = None
    if isinstance(edu, list) and edu:
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
    if company: bullets.append(f"Entreprise : {company}")
    if location: bullets.append(f"Localisation : {location}")
    if responsibilities: bullets.append("Responsabilités : " + ", ".join(_top([str(r) for r in responsibilities], 3)))
    if requirements: bullets.append("Pré-requis : " + ", ".join(_top([str(r) for r in requirements], 3)))
    if required_skills: bullets.append("Compétences demandées : " + ", ".join(_top([str(s) for s in required_skills], 6)))

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

# -------------------- HELPERS RECOMMANDATIONS --------------------
def _norm_list(x):
    return x if isinstance(x, list) else (x or [])

KNOWN_CERTS = {
    "aws": [
        {"certification": "AWS Certified Cloud Practitioner", "priority": "Moyenne", "relevance": "AWS"},
        {"certification": "AWS Solutions Architect – Associate", "priority": "Haute", "relevance": "AWS"},
    ],
    "azure": [
        {"certification": "Microsoft Azure Fundamentals (AZ-900)", "priority": "Moyenne", "relevance": "Azure"},
        {"certification": "Azure Administrator Associate (AZ-104)", "priority": "Haute", "relevance": "Azure"},
    ],
    "gcp": [{"certification": "Google Associate Cloud Engineer", "priority": "Moyenne", "relevance": "GCP"}],
    "kubernetes": [{"certification": "CKA - Certified Kubernetes Administrator", "priority": "Haute", "relevance": "Kubernetes"}],
    "docker": [{"certification": "Docker Certified Associate", "priority": "Moyenne", "relevance": "Docker"}],
    "elastic": [{"certification": "Elastic Certified Engineer", "priority": "Haute", "relevance": "ELK Stack"}],
    "elk": [{"certification": "Elastic Certified Engineer", "priority": "Haute", "relevance": "ELK Stack"}],
    "oracle": [{"certification": "Oracle Certified Professional, SQL and PL/SQL", "priority": "Haute", "relevance": "Oracle/SQL"}],
    "sql": [{"certification": "Oracle Certified Professional, SQL and PL/SQL", "priority": "Haute", "relevance": "SQL"}],
    "java": [
        {"certification": "Oracle Certified Associate, Java SE Programmer", "priority": "Haute", "relevance": "Java"},
        {"certification": "Oracle Certified Professional, Java SE Programmer", "priority": "Moyenne", "relevance": "Java"},
    ],
    "python": [{"certification": "PCAP – Certified Associate in Python Programming", "priority": "Moyenne", "relevance": "Python"}],
}

def suggest_certs_for_skills(skills):
    out = []
    for s in skills:
        key = str(s).lower()
        added = False
        for k, certs in KNOWN_CERTS.items():
            if k in key:
                out.extend(certs); added = True; break
        if not added:
            out.append({"certification": f"Certification {s}", "priority": "Moyenne", "relevance": str(s)})
    # unicité
    seen = set(); uniq = []
    for c in out:
        name = c.get("certification") or c.get("title") or c.get("name")
        if name and name not in seen:
            uniq.append(c); seen.add(name)
    return uniq[:8]

def suggest_projects_for_skills(skills):
    ideas = []
    for s in skills:
        t = str(s); low = t.lower()
        if "java" in low or "j2ee" in low:
            ideas.append("Application J2EE (CRUD + Auth + Tests)")
        elif "elk" in low or "elastic" in low:
            ideas.append("Analyse de logs avec ELK Stack (Filebeat → Logstash → ES → Kibana)")
        elif "sql" in low or "oracle" in low:
            ideas.append("Optimisation de requêtes SQL et modélisation relationnelle")
        elif "kubernetes" in low:
            ideas.append("Déploiement applicatif sur Kubernetes (Ingress, HPA, ConfigMaps)")
        elif "docker" in low:
            ideas.append("Containerisation d’un microservice + CI/CD")
        elif "aws" in low:
            ideas.append("Serverless sur AWS (API Gateway + Lambda + DynamoDB)")
        else:
            ideas.append(f"Mini-projet appliquant {t}")
    # unicité
    seen = set(); uniq = []
    for p in ideas:
        if p not in seen:
            uniq.append(p); seen.add(p)
    return uniq[:8]

def _ordered_unique(seq):
    seen = set()
    out = []
    for x in seq:
        k = str(x).strip().lower()
        if k and k not in seen:
            out.append(str(x).strip())
            seen.add(k)
    return out

def build_recommendations_from_match_and_quiz(match: Dict[str, Any], quiz_eval: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construit des recommandations à partir:
      - match: résultat du /api/match (missing_keywords, weak_areas, skill_analysis, parsed_job, score...)
      - quiz_eval: résultat du /api/quiz/evaluate (detailed_results, percentage...)
    Priorité: missing_keywords (JD), weak_areas (matching), erreurs quiz (skill_area),
              puis skills faibles détectés (skill_analysis.low_job_skill_matches).
    """
    missing = _norm_list((match or {}).get("missing_keywords"))
    weak_areas = _norm_list((match or {}).get("weak_areas"))
    skill_analysis = (match or {}).get("skill_analysis", {}) or {}
    parsed_job = (match or {}).get("parsed_job", {}) or {}

    low_job_skill_matches = _norm_list(skill_analysis.get("low_job_skill_matches"))  # liste de dicts?
    low_job_skills = []
    for item in low_job_skill_matches:
        if isinstance(item, dict):
            name = _first_non_empty(item.get("job_skill"), item.get("skill"), item.get("name"))
            if name: low_job_skills.append(name)
        elif isinstance(item, str):
            low_job_skills.append(item)

    # Erreurs quiz -> skill areas ratées
    quiz_bad_areas = []
    if quiz_eval:
        for dr in _norm_list(quiz_eval.get("detailed_results")):
            if not dr.get("is_correct"):
                area = dr.get("skill_area")
                if area: quiz_bad_areas.append(area)

    # Fallback côté JD si peu d'éléments
    jd_required = _norm_list(parsed_job.get("required_skills"))[:5]

    # Construction d'une liste pondérée puis dédoublonnée en conservant l'ordre
    priority_stack = []
    priority_stack += [f"{s}" for s in missing] * 3           # très prioritaire
    priority_stack += [f"{s}" for s in weak_areas] * 2        # prioritaire
    priority_stack += [f"{s}" for s in quiz_bad_areas] * 2    # prioritaire (quiz)
    priority_stack += [f"{s}" for s in low_job_skills]        # utile
    if not priority_stack:
        priority_stack += [f"{s}" for s in jd_required]

    focus_skills = _ordered_unique(priority_stack)[:10]

    # Génération des recos
    certifications = suggest_certs_for_skills(focus_skills)
    projects = suggest_projects_for_skills(focus_skills)
    learning_plan = [
        "S1 : Reprendre les bases des 2–3 compétences les plus faibles.",
        "S2 : Mise en pratique guidée (exos ciblés) + flashcards.",
        "S3 : Mini-projet tiré de la JD, code revu.",
        "S4 : Quiz de consolidation sur ces compétences.",
        "S5 : Préparation certification (banque de questions)."
    ]

    # Contexte & métriques
    rationale = {
        "matching_score": (match or {}).get("score"),
        "quiz_percentage": (quiz_eval or {}).get("percentage") if quiz_eval else None,
        "used_signals": {
            "missing_keywords": missing,
            "weak_areas": weak_areas,
            "quiz_incorrect_areas": quiz_bad_areas,
            "low_job_skills": low_job_skills
        }
    }

    return {
        "focus_skills": focus_skills,
        "certifications": certifications,
        "projects": projects,
        "learning_plan": learning_plan,
        "rationale": rationale
    }

# -------------------- AUTH --------------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email'); password = data.get('password')
    firstName = data.get('firstName'); lastName = data.get('lastName')
    if not email or not password:
        return jsonify({'success': False, 'error': 'Email et mot de passe requis'}), 400
    if users_collection.find_one({'email': email}):
        return jsonify({'success': False, 'error': 'Email déjà utilisé'}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    user = {'email': email, 'password': pw_hash, 'firstName': firstName, 'lastName': lastName,
            'createdAt': datetime.now(timezone.utc).isoformat()}
    result = users_collection.insert_one(user)

    access_token = create_access_token(identity=str(result.inserted_id), expires_delta=timedelta(hours=1))
    return jsonify({'success': True, 'message': 'Utilisateur créé',
                    'accessToken': access_token,
                    'user': {'id': str(result.inserted_id), 'email': email, 'firstName': firstName, 'lastName': lastName}}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email'); password = data.get('password')
    user = users_collection.find_one({'email': email})
    if not user:
        return jsonify({'success': False, 'error': 'Identifiant (email) incorrect'}), 401
    if not bcrypt.check_password_hash(user['password'], password):
        return jsonify({'success': False, 'error': 'Mot de passe incorrect'}), 401

    access_token = create_access_token(identity=str(user['_id']), expires_delta=timedelta(hours=1))
    return jsonify({'success': True, 'accessToken': access_token,
                    'user': {'id': str(user['_id']), 'email': user['email'],
                             'firstName': user.get('firstName'), 'lastName': user.get('lastName')}})

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

# -------------------- ENDPOINTS UTILES --------------------
@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Serveur de matching CV actif',
                    'status': 'ok',
                    'endpoints': ['/api/upload','/api/parse-cv','/api/parse-job','/api/match','/api/assistant/cards','/api/assistant/recommendations','/api/chat','/api/quiz']})

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok',
                    'model_available': bool(similarity_calculator and getattr(similarity_calculator, 'model', None)),
                    'model_type': getattr(similarity_calculator, 'model_type', 'none')})

# Upload/extraction texte
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify({'error': 'Aucun fichier fourni'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    if not allowed_file(file.filename): return jsonify({'error': 'Type de fichier non supporté'}), 400

    tmp = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(tmp)
    try:
        extracted_text = extract_text(tmp)
        warning = ""
        if not extracted_text.strip():
            warning = "Aucun texte détecté. PDF scanné ? Utilisez un PDF texte ou un OCR."
        elif len(extracted_text.strip()) < 50:
            warning = "Texte très court détecté. Vérifiez la qualité du fichier."
        return jsonify({'text': extracted_text, 'filename': file.filename, 'warning': warning, 'success': True})
    except Exception as e:
        return jsonify({'error': f"Erreur d'extraction: {e}"}), 500
    finally:
        if os.path.exists(tmp): os.remove(tmp)

# Parse CV
@app.route('/api/parse-cv', methods=['POST'])
@jwt_required()
def parse_cv():
    data = request.get_json() or {}
    cv_text = (data.get('cvText') or '').strip()
    if not cv_text: return jsonify({'error': 'Texte CV manquant'}), 400

    try:
        parsed = parse_cv_with_gemini(cv_text)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
    except Exception as e:
        return jsonify({'error': f'Erreur parsing CV: {e}'}), 500

    save_result_to_db(get_jwt_identity(), "cv", parsed, {"source": "gemini_parser", "original_text_length": len(cv_text)})
    return jsonify({'parsed_cv': parsed, 'success': True})

# Parse Job
@app.route('/api/parse-job', methods=['POST'])
@jwt_required()
def parse_job_description():
    data = request.get_json() or {}
    job_text = (data.get('jobText') or '').strip()
    if not job_text: return jsonify({'error': 'Texte job description manquant'}), 400
    try:
        parsed_job = parse_job(job_text)
    except Exception as e:
        return jsonify({'error': f'Erreur parsing job: {e}'}), 500

    save_result_to_db(get_jwt_identity(), "job", parsed_job, {"source": "job_parser", "original_text_length": len(job_text)})
    return jsonify({'parsed_job': parsed_job, 'success': True})

# MATCH
@app.route('/api/match', methods=['POST'])
@jwt_required()
def calculate_matching():
    try:
        data = request.get_json() or {}
        cv_text = (data.get('cvText') or '').strip()
        job_text = (data.get('jobText') or '').strip()
        if not cv_text or not job_text:
            return jsonify({'error': 'CV et job description requis'}), 400
        if not (similarity_calculator and getattr(similarity_calculator, 'model', None)):
            return jsonify({'error': 'Modèle de similarité non disponible'}), 500

        # parse
        try:
            parsed_cv = parse_cv_with_gemini(cv_text)
            if isinstance(parsed_cv, str):
                parsed_cv = json.loads(parsed_cv)
        except Exception as e:
            return jsonify({'error': f'Erreur parsing CV: {e}'}), 500

        try:
            parsed_job = parse_job(job_text)
        except Exception as e:
            return jsonify({'error': f'Erreur parsing job: {e}'}), 500

        # autosave last job
        try:
            save_result_to_db(get_jwt_identity(), "job", parsed_job,
                              {"source": "match_endpoint_autosave", "original_text_length": len(job_text)})
        except Exception as e:
            app.logger.warning(f"Autosave job failed: {e}")

        # similarity
        sim = similarity_calculator.calculate_comprehensive_embedding_similarity(parsed_cv, parsed_job)

        # missing keywords
        cv_skills = parsed_cv.get('skills', []) if parsed_cv else []
        job_skills = parsed_job.get('required_skills', []) if parsed_job else []
        cv_skills_lower = [str(s).lower() for s in cv_skills]
        missing_keywords = [s for s in job_skills if str(s).lower() not in cv_skills_lower]

        # suggestions
        overall = sim.get('overall_similarity_score', 0)
        suggestions = []
        if overall < 40:
            suggestions.append("Votre profil semble peu adapté à ce poste.")
        elif overall < 55:
            suggestions.append("Ajoutez plus de compétences techniques mentionnées dans l'offre.")
        elif overall < 70:
            suggestions.append("Mettez davantage en avant votre expérience pertinente.")
        else:
            suggestions.append("Excellent match ! Mettez en avant vos points forts.")
        if missing_keywords:
            suggestions.append(f"À travailler : {', '.join(missing_keywords[:3])}")

        matching_data = {
            'score': overall,
            'similarity_level': sim.get('similarity_level', 'Calculé'),
            'sectional_scores': sim.get('sectional_scores', {}),
            'skill_analysis': sim.get('skill_analysis', {}),
            'weak_areas': sim.get('weak_areas', []),
            'missing_keywords': missing_keywords,
            'suggestions': suggestions,
            'method': f"Embedding similarity ({sim.get('model_used', 'sentence_transformer')})",
            'parsed_cv': parsed_cv,
            'parsed_job': parsed_job,
            'success': True
        }

        # ---- Recommandations (basées sur matching + quiz) ----
        user_id = get_jwt_identity()
        latest_quiz_eval = db.results.find_one({"user": ObjectId(user_id), "type": "quiz_evaluation"}, sort=[("createdAt", -1)])
        quiz_payload = (latest_quiz_eval or {}).get("data")
        recommendations = build_recommendations_from_match_and_quiz(matching_data, quiz_payload)
        matching_data["recommendations"] = recommendations

        # save
        save_result_to_db(
            user_id=user_id,
            result_type="matching",
            data=matching_data,
            meta={"model_used": sim.get("model_used", "sentence_transformer"),
                  "cv_text_length": len(cv_text), "job_text_length": len(job_text)},
            refs={"cv_skills_count": len(cv_skills),
                  "job_skills_count": len(job_skills),
                  "missing_skills_count": len(missing_keywords)}
        )
        return jsonify(matching_data)
    except Exception as e:
        return jsonify({'error': f'Erreur matching: {e}'}), 500

# Assistant cards
@app.route('/api/assistant/cards', methods=['GET'])
@jwt_required()
def get_assistant_cards():
    try:
        user_id = get_jwt_identity()
        obj_id = ObjectId(user_id)

        user = users_collection.find_one({'_id': obj_id}, {'password': 0}) or {}

        latest_cv_result = db.results.find_one({"user": obj_id, "type": "cv"}, sort=[("createdAt", -1)])
        cv_card = None
        if latest_cv_result and latest_cv_result.get("data"):
            cv_data = latest_cv_result["data"]
            if isinstance(cv_data, dict) and "parsed_cv" in cv_data:
                cv_data = cv_data["parsed_cv"]
            cv_card = summarize_cv_for_card(cv_data)

        latest_job_result = db.results.find_one({"user": obj_id, "type": "job"}, sort=[("createdAt", -1)])
        job_card = None
        if latest_job_result and latest_job_result.get("data"):
            job_card = summarize_job_for_card(latest_job_result["data"])

        if not job_card or not cv_card:
            latest_match = db.results.find_one({"user": obj_id, "type": "matching"}, sort=[("createdAt", -1)])
            if latest_match:
                mdata = latest_match.get("data", {})
                if not job_card and isinstance(mdata.get("parsed_job"), dict):
                    job_card = summarize_job_for_card(mdata["parsed_job"])
                if not cv_card and isinstance(mdata.get("parsed_cv"), dict):
                    cv_card = summarize_cv_for_card(mdata["parsed_cv"])

        cv_count = db.results.count_documents({"user": obj_id, "type": "cv"})
        job_count = db.results.count_documents({"user": obj_id, "type": "job"})
        quiz_count = db.results.count_documents({"user": obj_id, "type": {"$in": ["quiz", "quiz_evaluation"]}})

        profile_card = build_profile_card(user, {"cv_count": cv_count, "job_count": job_count, "quiz_count": quiz_count})
        return jsonify({"success": True, "cards": {"profile": profile_card, "cv": cv_card, "job": job_card}})
    except Exception as e:
        return jsonify({"success": False, "error": f"Erreur assistant: {e}"}), 500

# Recommandations (appelées depuis ChatSection bouton "Recos")
@app.route('/api/assistant/recommendations', methods=['GET'])
@jwt_required()
def assistant_recommendations():
    try:
        user_id = get_jwt_identity()
        oid = ObjectId(user_id)

        latest_match = db.results.find_one({"user": oid, "type": "matching"}, sort=[("createdAt", -1)])
        latest_quiz_eval = db.results.find_one({"user": oid, "type": "quiz_evaluation"}, sort=[("createdAt", -1)])

        if not latest_match:
            return jsonify({"success": False, "error": "Aucun résultat de matching trouvé. Lancez d'abord une analyse de compatibilité."}), 400

        mdata = latest_match.get("data", {}) or {}
        recos = mdata.get("recommendations")

        # Si pas de recos sauvegardées ou si l’on veut rafraîchir avec le quiz le plus récent, on recalcule
        quiz_payload = (latest_quiz_eval or {}).get("data")
        if not recos:
            recos = build_recommendations_from_match_and_quiz(mdata, quiz_payload)

        messages = []
        if recos.get("certifications"):
            messages.append({"type": "certs", "items": recos["certifications"]})
        if recos.get("projects"):
            messages.append({"type": "projects", "items": recos["projects"]})
        if recos.get("learning_plan"):
            messages.append({"type": "insight", "text": "📚 Plan d’apprentissage disponible dans les recommandations."})
        if recos.get("focus_skills"):
            messages.append({"type": "focus", "items": recos["focus_skills"]})

        return jsonify({"success": True, "messages": messages, "recommendations": recos})
    except Exception as e:
        return jsonify({"success": False, "error": f"Endpoint recommandations: {e}"}), 500

# -------------------- CHAT --------------------
@app.route('/api/chat', methods=['POST'])
@jwt_required(optional=True)
def chat_with_gemini():
    try:
        payload = request.get_json() or {}
        incoming = payload.get("messages", [])

        sys = next((m.get("content") for m in incoming if m.get("role") == "system"), None)
        system_instruction = sys or (
            "Tu es un assistant utile spécialisé en recrutement. "
            "Réponds en FRANÇAIS, de façon claire et concise. "
            "Si la question concerne le candidat, appuie-toi sur le CV et la Job Description si disponibles."
        )

        user_id = get_jwt_identity()
        ctx_lines = []
        if user_id:
            obj_id = ObjectId(user_id)
            latest_cv = db.results.find_one({"user": obj_id, "type": "cv"}, sort=[("createdAt", -1)])
            latest_job = db.results.find_one({"user": obj_id, "type": "job"}, sort=[("createdAt", -1)])
            if latest_cv and latest_cv.get("data"):
                cv_data = latest_cv["data"].get("parsed_cv", latest_cv["data"])
                cv_card = summarize_cv_for_card(cv_data)
                ctx_lines.append(f"[CV] {cv_card['title']} — {cv_card['subtitle']}. " + " | ".join(cv_card.get("bullets", [])))
            if latest_job and latest_job.get("data"):
                job_card = summarize_job_for_card(latest_job["data"])
                ctx_lines.append(f"[JOB] {job_card['title']} — {job_card['subtitle']}. " + " | ".join(job_card.get("bullets", [])))
        context_blob = "\n".join(ctx_lines) if ctx_lines else ""

        history = []
        for m in incoming:
            role = m.get("role"); content = m.get("content", "")
            if role == "user": history.append({"role": "user", "parts": [content]})
            elif role == "assistant": history.append({"role": "model", "parts": [content]})

        chat_model = genai.GenerativeModel("gemini-1.5-flash",
                                           system_instruction=system_instruction + ("\n\nContexte:\n" + context_blob if context_blob else ""))
        resp = chat_model.generate_content(history if history else [{"role": "user", "parts": ["Bonjour"]}])
        text = (resp.text or "").strip() or "(Réponse vide)"
        return jsonify({"message": {"role": "assistant", "content": text}, "success": True})
    except Exception as e:
        return jsonify({"error": f"Erreur chat: {e}"}), 500

# -------------------- QUIZ --------------------
# Helpers additionnels pour extraire proprement les compétences du CV
def _normalize_skill_list(skills_raw) -> List[str]:
    """
    Accepte une liste de strings ou d'objets et renvoie une liste de noms de compétences (strings).
    Exemples d'objets supportés: {"name": "Python"}, {"skill": "Docker"}, {"title": "Kubernetes"}
    """
    if not isinstance(skills_raw, list):
        return []
    out = []
    for s in skills_raw:
        if isinstance(s, str):
            name = s.strip()
        elif isinstance(s, dict):
            name = _first_non_empty(s.get("name"), s.get("skill"), s.get("title"), s.get("label"))
        else:
            name = None
        if name:
            out.append(name)
    # unicité en conservant l'ordre
    seen = set()
    uniq = []
    for n in out:
        low = n.lower()
        if low not in seen:
            uniq.append(n)
            seen.add(low)
    return uniq

def _pick_focus_skills_from_cv(parsed_cv: Dict[str, Any], max_n: int = 8) -> List[str]:
    """
    Récupère les compétences du CV (avec normalisation) et en sélectionne jusqu'à max_n.
    """
    skills_raw = (parsed_cv or {}).get("skills", []) or []
    skills = _normalize_skill_list(skills_raw)
    return skills[:max_n]

@app.route('/api/quiz', methods=['POST'])
@jwt_required()
def generate_quiz():
    """
    Génére un quiz ciblé SUR LES COMPÉTENCES DU CV.
    - Échec si aucun CV n'est trouvé pour l'utilisateur.
    - Utilise QuizGenerator avec focus_skills = compétences extraites du CV.
    """
    data = request.get_json() or {}
    level = data.get('level', 'moyen')
    count = data.get('count', 5)
    user_id = get_jwt_identity()

    if not quiz_generator:
        return jsonify({'error': 'Générateur non disponible'}), 500

    # 1) Récupère le dernier CV parsé enregistré pour l’utilisateur
    latest_cv_doc = db.results.find_one({"user": ObjectId(user_id), "type": "cv"}, sort=[("createdAt", -1)])
    if not latest_cv_doc or not latest_cv_doc.get("data"):
        return jsonify({
            'error': "Aucun CV trouvé. Veuillez uploader et parser votre CV avant de générer un quiz ciblé."
        }), 400

    # Le CV peut être stocké sous data['parsed_cv'] ou directement data
    cv_data = latest_cv_doc["data"]
    parsed_cv = cv_data["parsed_cv"] if isinstance(cv_data, dict) and "parsed_cv" in cv_data else cv_data

    # 2) Profil utilisateur basé sur le CV (pour contexte du générateur)
    profile = {
        'name': parsed_cv.get('name', 'Candidat'),
        'skills': parsed_cv.get('skills', []),
        'education': parsed_cv.get('education', []),
        'experience': parsed_cv.get('experience', []),
        'languages': parsed_cv.get('languages', []),
        'certifications': parsed_cv.get('certifications', []),
    }

    # 3) Déterminer les compétences ciblées (focus_skills) à partir du CV
    focus_skills = _pick_focus_skills_from_cv(parsed_cv, max_n=8)
    if not focus_skills:
        return jsonify({
            'error': "Votre CV ne contient pas de compétences exploitables. Veuillez vérifier l’extraction de votre CV."
        }), 400

    # 4) Niveaux mappés
    level_map = {'facile': 'débutant', 'moyen': 'intermédiaire', 'difficile': 'avancé'}
    mapped_level = level_map.get(level, 'intermédiaire')

    # 5) Génération du quiz ciblé sur ces compétences
    try:
        quiz = quiz_generator.generate_quiz(
            user_profile=profile,
            level=mapped_level,
            num_questions=count,
            focus_skills=focus_skills  # ⬅️ ciblage explicite sur les compétences du CV
        )
    except TypeError:
        # Compat rétro si l’implémentation n’a pas encore le param focus_skills
        quiz = quiz_generator.generate_quiz(
            user_profile=profile,
            level=mapped_level,
            num_questions=count
        )

    if not quiz:
        return jsonify({'error': 'Génération échouée'}), 500

    # 6) Normalisation des questions (suppression des préfixes a), b) ...)
    questions = []
    for i, q in enumerate(quiz.questions):
        clean_choices = [(opt.split(') ', 1)[1] if ') ' in opt else opt) for opt in q.options]
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
            'profile_used': profile.get('name', 'Utilisateur'),
            'skills_detected': len(profile.get('skills', [])),
            'focus_skills': focus_skills  # ⬅️ visible côté client si besoin
        }
    }

    # 7) Sauvegarde
    save_result_to_db(
        user_id,
        "quiz",
        quiz_data,
        meta={
            "level": level,
            "mapped_level": mapped_level,
            "questions_count": count,
            "generated_questions": len(questions),
            "profile_source": "cv_parsing",
            "using_cv_skills": True,
            "focus_skills_count": len(focus_skills)
        }
    )
    return jsonify(quiz_data)

def get_user_profile_from_cv(user_id):
    try:
        latest_cv = db.results.find_one({"user": ObjectId(user_id), "type": "cv"}, sort=[("createdAt", -1)])
        if latest_cv and latest_cv.get('data'):
            cv_data = latest_cv['data']
            cv_parsed = cv_data['parsed_cv'] if isinstance(cv_data, dict) and 'parsed_cv' in cv_data else cv_data
            return {'name': cv_parsed.get('name', 'Candidat'),
                    'skills': cv_parsed.get('skills', []),
                    'education': cv_parsed.get('education', []),
                    'experience': cv_parsed.get('experience', []),
                    'languages': cv_parsed.get('languages', []),
                    'certifications': cv_parsed.get('certifications', [])}
        else:
            # Fallback: profil générique (utilisé ailleurs)
            user = users_collection.find_one({'_id': ObjectId(user_id)}) or {}
            return {'name': f"{user.get('firstName','')} {user.get('lastName','')}".strip() or 'Candidat',
                    'skills': ['Développement', 'Programmation', 'Informatique'],
                    'education': [{'degree': 'Formation générale'}],
                    'experience': [{'title': 'Expérience professionnelle', 'duration': 'Variable'}],
                    'languages': ['Français'], 'certifications': []}
    except Exception as e:
        print(f"❌ Profil CV error: {e}")
        return {'name': 'Candidat', 'skills': ['JavaScript', 'Python', 'HTML', 'CSS', 'React'],
                'education': [{'degree': 'Formation dev'}], 'experience': [{'title': 'Développeur', 'duration': '2 ans'}],
                'languages': ['Français'], 'certifications': []}

@app.route('/api/quiz/profile-status', methods=['GET'])
@jwt_required()
def get_quiz_profile_status():
    try:
        user_id = get_jwt_identity()
        latest_cv = db.results.find_one({"user": ObjectId(user_id), "type": "cv"}, sort=[("createdAt", -1)])
        if latest_cv:
            cv_data = latest_cv.get('data', {})
            cv_parsed = cv_data['parsed_cv'] if isinstance(cv_data, dict) and 'parsed_cv' in cv_data else cv_data
            return jsonify({'has_cv': True, 'profile_name': cv_parsed.get('name', 'Candidat'),
                            'skills_count': len(cv_parsed.get('skills', [])),
                            'experience_count': len(cv_parsed.get('experience', [])),
                            'last_updated': latest_cv.get('createdAt'),
                            'recommendation': 'Quiz personnalisé basé sur votre CV'})
        else:
            return jsonify({'has_cv': False, 'profile_name': 'Profil générique', 'skills_count': 5, 'experience_count': 1,
                            'last_updated': None, 'recommendation': 'Uploadez votre CV pour des quiz personnalisés'})
    except Exception as e:
        return jsonify({'error': f'Erreur statut: {e}'}), 500

@app.route('/api/quiz/evaluate', methods=['POST'])
@jwt_required()
def evaluate_quiz():
    try:
        data = request.get_json() or {}
        answers = data.get('answers', {}); questions_data = data.get('questions', [])
        if not questions_data: return jsonify({'error': "Questions manquantes"}), 400

        quiz_questions = []
        for q in questions_data:
            quiz_questions.append(QuizQuestion(
                question=q['question'], options=q['choices'], correct_answer=q['answerIndex'],
                explanation=q.get('explanation', ''), skill_area=q.get('skillArea', 'Général'),
                difficulty=q.get('difficulty', 'moyen')
            ))
        quiz = Quiz(title="Évaluation Candidat", description="Quiz évalué par Gemini",
                    level="moyen", questions=quiz_questions, estimated_duration=len(quiz_questions)*2)
        evaluator = QuizEvaluator()
        results = evaluator.evaluate_answers(quiz, {i: answers.get(str(q.get('id', i)), -1) for i, q in enumerate(questions_data)})

        detailed_results = []
        for i, ua in enumerate(results.user_answers):
            q = quiz.questions[i]
            user_index = ua.selected_option
            user_text = q.options[user_index] if user_index >= 0 else "Aucune réponse"
            detailed_results.append({'question_id': i, 'question': q.question,
                                     'user_answer': user_text, 'correct_answer': q.options[q.correct_answer],
                                     'is_correct': ua.is_correct, 'explanation': q.explanation, 'skill_area': q.skill_area})

        percentage = round(results.percentage, 1)
        feedback = generate_feedback(percentage, detailed_results)
        evaluation_data = {'success': True, 'score': results.score, 'total': results.total_questions,
                           'percentage': percentage, 'detailed_results': detailed_results, 'feedback': feedback}

        user_id = get_jwt_identity()
        save_result_to_db(user_id, "quiz_evaluation", evaluation_data,
                          {"questions_count": len(questions_data), "answers_provided": len([a for a in answers.values() if a >= 0])},
                          {"score": results.score, "percentage": results.percentage})
        return jsonify(evaluation_data)
    except Exception as e:
        return jsonify({'error': f'Erreur évaluation: {e}'}), 500

# -------------------- RESULTS API --------------------
@app.route('/api/results', methods=['POST'])
@jwt_required()
def save_result():
    data = request.get_json() or {}
    if "type" not in data or "data" not in data: return jsonify({"error": "type & data requis"}), 400
    user_id = get_jwt_identity()
    result = create_result(user_id, data["type"], data["data"], data.get("meta"), data.get("refs"))
    db.results.insert_one(result)
    result["_id"] = str(result["_id"]); result["user"] = str(result["user"])
    return jsonify(result), 201

@app.route('/api/results', methods=['GET'])
@jwt_required()
def get_results():
    user_id = get_jwt_identity()
    type_filter = request.args.get("type"); page = int(request.args.get("page", 1)); limit = int(request.args.get("limit", 20))
    query = {"user": ObjectId(user_id)}; 
    if type_filter: query["type"] = type_filter
    cursor = db.results.find(query).sort("createdAt", -1).skip((page-1)*limit).limit(limit)
    results = []
    for r in cursor:
        r["_id"] = str(r["_id"]); r["user"] = str(r["user"]); results.append(r)
    return jsonify(results), 200

# -------------------- ERRORS --------------------
@app.errorhandler(404)
def not_found(error): return jsonify({'error': 'Endpoint non trouvé'}), 404

@app.errorhandler(500)
def internal_error(error): return jsonify({'error': 'Erreur interne du serveur'}), 500

# -------------------- RUN --------------------
if __name__ == '__main__':
    print("🚀 Server up on :3001")
    app.run(debug=True, host='0.0.0.0', port=3001, threaded=True)
