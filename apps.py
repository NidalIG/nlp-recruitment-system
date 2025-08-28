# app.py - Backend Flask principal corrigé
import os
import json
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Imports de vos modules existants
from cv_parsing.extractors import extract_text
from cv_parsing.gemini_parser import parse_cv_with_gemini
from cv_parsing.job_parsing import parse_job
from cv_job_matching import CVJobEmbeddingSimilarity

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Instance globale du calculateur de similarité
try:
    similarity_calculator = CVJobEmbeddingSimilarity(model_type="sentence_transformer")
    print("✅ SentenceTransformer chargé avec succès")
except Exception as e:
    print(f"❌ Erreur chargement modèle: {e}")
    similarity_calculator = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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