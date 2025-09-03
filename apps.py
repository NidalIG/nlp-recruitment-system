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
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    users_collection.insert_one(user)
    return jsonify({'success': True, 'message': 'Utilisateur créé avec succès'}), 201


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
    expires_delta=timedelta(hours=1)  # <-- juste timedelta, pas datetime.timedelta
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
        
        return jsonify({
            'parsed_cv': parsed_data,
            'success': True
        })
    
    except Exception as e:
        return jsonify({'error': f'Erreur parsing CV: {str(e)}'}), 500

@app.route('/api/parse-job', methods=['POST'])
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
        
        return jsonify({
            'parsed_job': parsed_job,
            'success': True
        })
    
    except Exception as e:
        return jsonify({'error': f'Erreur parsing job: {str(e)}'}), 500

@app.route('/api/match', methods=['POST'])
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
        
        try:
            parsed_job = parse_job(job_text)
        except Exception as e:
            return jsonify({'error': f'Erreur parsing job: {str(e)}'}), 500
        
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
            
            return jsonify({
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
            })
        
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
def generate_quiz():
    """Génère un quiz simplifié"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400
        
        level = data.get('level', 'moyen')
        count = data.get('count', 5)
        
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
        
        # Profil utilisateur générique
        user_profile = {
            'name': 'Candidat',
            'skills': ['JavaScript', 'Python', 'HTML', 'CSS', 'React', 'SQL'],
            'education': [{'degree': 'Formation développement'}],
            'experience': [{'title': 'Développeur', 'duration': '2 ans'}]
        }
        
        # Génération du quiz
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
        
        return jsonify({
            'success': True,
            'questions': questions,
            'quiz_info': {
                'title': quiz.title,
                'description': quiz.description,
                'estimated_duration': quiz.estimated_duration,
                'level': level
            }
        })
    
    except Exception as e:
        print(f"❌ Erreur génération quiz: {str(e)}")
        return jsonify({'error': f'Erreur: {str(e)}'}), 500

def generate_feedback(percentage, detailed_results):
    raise NotImplementedError

@app.route('/api/quiz/evaluate', methods=['POST'])
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

        return jsonify({
            'success': True,
            'score': results.score,
            'total': results.total_questions,
            'percentage': round(results.percentage, 1),
            'detailed_results': detailed_results,
            'feedback': feedback
        })

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
    
