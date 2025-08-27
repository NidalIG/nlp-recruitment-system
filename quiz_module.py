# Générateur de Quiz de Recrutement avec Gemini API
import json
import google.generativeai as genai
from typing import Dict, List, Literal
from dataclasses import dataclass
import os
from datetime import datetime

# Configuration de l'API Gemini avec paramètres optimisés
GEMINI_API_KEY = "AIzaSyCGScegfQ9kF4zcLErYf3cTFE9XTa_v1Pw"  
genai.configure(api_key=GEMINI_API_KEY)

# Initialisation du modèle Gemini avec configuration pour JSON
generation_config = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 40,
    "max_output_tokens": 2048,
}

model = genai.GenerativeModel(
    'gemini-1.5-flash',
    generation_config=generation_config
)

@dataclass
class QuizQuestion:
    """Structure d'une question de quiz"""
    question: str
    options: List[str]
    correct_answer: int
    explanation: str
    skill_area: str
    difficulty: str

@dataclass
class Quiz:
    """Structure complète d'un quiz"""
    title: str
    description: str
    level: str
    questions: List[QuizQuestion]
    estimated_duration: int  # en minutes

class ProfileAnalyzer:
    """Classe pour analyser le profil utilisateur et extraire les compétences clés"""
    
    def __init__(self, user_profile: Dict):
        self.profile = user_profile
    
    def get_primary_skills(self) -> List[str]:
        """Extrait les compétences principales du profil"""
        return self.profile.get('skills', [])
    
    def get_experience_level(self) -> str:
        """Détermine le niveau d'expérience basé sur l'éducation et l'expérience"""
        experience = self.profile.get('experience', [])
        education = self.profile.get('education', [])
        
        # Logique simple pour déterminer le niveau d'expérience
        if len(experience) == 0:
            return "débutant"
        elif len(experience) <= 2:
            return "intermédiaire" 
        else:
            return "avancé"
    
    def get_domain_focus(self) -> List[str]:
        """Identifie les domaines de spécialisation principaux"""
        skills = self.get_primary_skills()
        domains = []
        
        # Catégorisation des compétences par domaine
        web_dev_skills = ['JavaScript', 'React', 'Angular', 'Spring Boot', 'HTML', 'CSS']
        data_science_skills = ['Data Science', 'Machine Learning', 'Deep Learning', 'Python', 'AI']
        database_skills = ['SQL', 'MySQL', 'PostgreSQL']
        
        if any(skill in skills for skill in web_dev_skills):
            domains.append("Développement Web")
        if any(skill in skills for skill in data_science_skills):
            domains.append("Data Science & IA")
        if any(skill in skills for skill in database_skills):
            domains.append("Bases de Données")
            
        return domains if domains else ["Développement Général"]

class QuizGenerator:
    """Générateur de quiz utilisant Gemini API"""
    
    def __init__(self, model):
        self.model = model
    
    def create_structured_prompt(self, profile_analyzer: ProfileAnalyzer, 
                                level: Literal["bas", "intermédiaire", "avancé"], 
                                num_questions: int = 10) -> str:
        """Crée un prompt structuré pour Gemini"""
        
        skills = profile_analyzer.get_primary_skills()
        domains = profile_analyzer.get_domain_focus()
        
        # Définition des niveaux de difficulté
        level_descriptions = {
            "bas": "Questions fondamentales, concepts de base, syntaxe simple",
            "intermédiaire": "Applications pratiques, résolution de problèmes moyens, intégration de concepts",
            "avancé": "Optimisation, architecture, cas complexes, bonnes pratiques avancées"
        }
        
        prompt = f"""
        Vous êtes un expert en recrutement technique. Générez un quiz de {num_questions} questions pour évaluer un candidat.

        PROFIL DU CANDIDAT:
        - Nom: {profile_analyzer.profile.get('name', 'N/A')}
        - Compétences principales: {', '.join(skills[:5])}
        - Domaines de spécialisation: {', '.join(domains)}
        - Niveau ciblé: {level.upper()}

        NIVEAU DE DIFFICULTÉ "{level.upper()}":
        {level_descriptions[level]}

        INSTRUCTIONS STRICTES:
        1. Créez exactement {num_questions} questions QCM
        2. Chaque question doit avoir 4 options (A, B, C, D)
        3. Concentrez-vous sur les compétences du profil: {', '.join(skills)}
        4. Variez les domaines selon le profil
        5. Respectez le niveau de difficulté demandé

        FORMAT DE RÉPONSE (JSON strict - IMPORTANT):
        Répondez UNIQUEMENT avec le JSON suivant, sans aucun texte avant ou après:
        
        {{
            "quiz_title": "Quiz {level.title()} - [Domaine Principal]",
            "quiz_description": "Évaluation des compétences {level} en [domaines]",
            "estimated_duration": 15,
            "questions": [
                {{
                    "id": 1,
                    "question": "Votre question ici",
                    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                    "correct_answer": 0,
                    "explanation": "Explication détaillée",
                    "skill_area": "Nom de la compétence",
                    "difficulty": "{level}"
                }}
            ]
        }}

        ATTENTION: Répondez UNIQUEMENT avec ce JSON, sans texte d'introduction ni conclusion.
        
        Générez exactement {num_questions} questions au format ci-dessus.
        """
        
        return prompt
    
    def extract_json_from_response(self, response_text: str) -> dict:
        """Extrait le JSON de la réponse, même s'il est entouré d'autre texte"""
        import re
        
        # Chercher le JSON dans la réponse
        json_pattern = r'\{.*\}'
        json_match = re.search(json_pattern, response_text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Si pas de JSON trouvé, essayer de nettoyer la réponse
        cleaned_text = response_text.strip()
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith('```'):
            cleaned_text = cleaned_text[:-3]
        
        return json.loads(cleaned_text.strip())
    
    def generate_quiz(self, profile_analyzer: ProfileAnalyzer, 
                     level: Literal["bas", "intermédiaire", "avancé"], 
                     num_questions: int = 10) -> Quiz:
        """Génère un quiz complet"""
        
        try:
            prompt = self.create_structured_prompt(profile_analyzer, level, num_questions)
            
            # Appel à l'API Gemini
            print(f"📡 Génération du quiz niveau {level}...")
            response = self.model.generate_content(prompt)
            
            print(f"🔍 Réponse brute de l'API (premiers 200 caractères):")
            print(f"'{response.text[:200]}...'")
            
            # Extraction et parsing du JSON
            quiz_data = self.extract_json_from_response(response.text)
            
            print(f"✅ JSON parsé avec succès!")
            
            # Conversion en objets QuizQuestion
            questions = []
            for q_data in quiz_data['questions']:
                question = QuizQuestion(
                    question=q_data['question'],
                    options=q_data['options'],
                    correct_answer=q_data['correct_answer'],
                    explanation=q_data['explanation'],
                    skill_area=q_data['skill_area'],
                    difficulty=q_data['difficulty']
                )
                questions.append(question)
            
            # Création du quiz final
            quiz = Quiz(
                title=quiz_data['quiz_title'],
                description=quiz_data['quiz_description'],
                level=level,
                questions=questions,
                estimated_duration=quiz_data['estimated_duration']
            )
            
            print(f"🎯 Quiz créé: {quiz.title} ({len(quiz.questions)} questions)")
            return quiz
            
        except json.JSONDecodeError as e:
            print(f"❌ Erreur de parsing JSON: {str(e)}")
            print(f"📄 Réponse complète de l'API:")
            print(f"'{response.text}'")
            return None
        except Exception as e:
            print(f"❌ Erreur lors de la génération du quiz: {str(e)}")
            print(f"📄 Réponse de l'API (si disponible):")
            try:
                print(f"'{response.text}'")
            except:
                print("Pas de réponse disponible")
            return None

def display_quiz(quiz: Quiz):
    """Affiche le quiz de manière formatée"""
    if not quiz:
        print("❌ Aucun quiz à afficher")
        return
    
    print("=" * 60)
    print(f"🎯 {quiz.title}")
    print(f"📋 {quiz.description}")
    print(f"⏱️  Durée estimée: {quiz.estimated_duration} minutes")
    print(f"📊 Niveau: {quiz.level.title()}")
    print("=" * 60)
    
    for i, question in enumerate(quiz.questions, 1):
        print(f"\n❓ Question {i}: {question.question}")
        print(f"🎯 Domaine: {question.skill_area}")
        
        for option in question.options:
            print(f"   {option}")
        
        print(f"✅ Réponse correcte: {question.options[question.correct_answer]}")
        print(f"💡 Explication: {question.explanation}")
        print("-" * 40)

# EXEMPLE D'UTILISATION

# Profil utilisateur exemple
user_profile = {
    "name": "IGROU NIDAL",
    "email": "igrounidal0820@gmail.com",
    "phone": "0770445904",
    "skills": [
        "Full-Stack Development",
        "Data Science",
        "AI",
        "Machine Learning",
        "Deep Learning",
        "Java",
        "Python",
        "JavaScript",
        "SQL",
        "Spring Boot",
        "Angular",
        "React",
        "Git",
        "MySQL",
        "PostgreSQL"
    ],
    "education": [
        {
            "degree": "Master Intelligence Artificielle et Informatique Digitale",
            "institution_name": "Faculté des Sciences et Techniques, Béni Mellal",
            "graduation_year": "2025"
        }
    ],
    "experience": [
        {
            "job_title": "Développeuse Web",
            "company_name": "Allobaba",
            "years_worked": "March 2024 - June 2024",
            "description": "Développement d'une application web de gestion de facturation"
        }
    ]
}

def test_api_connection():
    """Teste la connexion à l'API Gemini"""
    try:
        response = model.generate_content("Dis juste 'API OK' en JSON: {\"status\": \"OK\"}")
        print(f"✅ Test API réussi: {response.text}")
        return True
    except Exception as e:
        print(f"❌ Erreur de connexion API: {str(e)}")
        print("🔧 Vérifiez que:")
        print("   1. Votre clé API est correcte")
        print("   2. Vous avez installé: pip install google-generativeai")
        print("   3. Votre quota API n'est pas épuisé")
        return False

def main():
    """Fonction principale pour tester le générateur"""
    
    print("🔧 Test de connexion API...")
    if not test_api_connection():
        return
    
    # ÉTAPE 1: Analyser le profil
    analyzer = ProfileAnalyzer(user_profile)
    
    print("\n🔍 ANALYSE DU PROFIL:")
    print(f"Nom: {analyzer.profile['name']}")
    print(f"Compétences principales: {analyzer.get_primary_skills()[:5]}")  # Limiter l'affichage
    print(f"Domaines de focus: {analyzer.get_domain_focus()}")
    print(f"Niveau d'expérience estimé: {analyzer.get_experience_level()}")
    
    # ÉTAPE 2: Créer le générateur
    generator = QuizGenerator(model)
    
    # ÉTAPE 3: Générer quiz pour un seul niveau d'abord (test)
    test_level = "intermédiaire"
    print(f"\n🚀 TEST - GÉNÉRATION QUIZ NIVEAU: {test_level.upper()}")
    print("=" * 50)
    
    quiz = generator.generate_quiz(analyzer, test_level, num_questions=10)
    
    if quiz:
        display_quiz(quiz)
        
        # Sauvegarder le quiz
        filename = f"quiz_{test_level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        if save_quiz_to_json(quiz, filename):
            print(f"💾 Quiz sauvegardé dans: {filename}")
    else:
        print(f"❌ Échec de génération pour le niveau {test_level}")
    
    print("\n" + "="*80)

# FONCTION UTILITAIRE pour sauvegarder le quiz
def save_quiz_to_json(quiz: Quiz, filename: str):
    """Sauvegarde le quiz en format JSON"""
    if not quiz:
        return False
    
    quiz_dict = {
        "title": quiz.title,
        "description": quiz.description,
        "level": quiz.level,
        "estimated_duration": quiz.estimated_duration,
        "generated_at": datetime.now().isoformat(),
        "questions": [
            {
                "question": q.question,
                "options": q.options,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "skill_area": q.skill_area,
                "difficulty": q.difficulty
            }
            for q in quiz.questions
        ]
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(quiz_dict, f, ensure_ascii=False, indent=2)
    
    return True

# Pour exécuter le script principal:
if __name__ == "__main__":
    print("🎓 GÉNÉRATEUR DE QUIZ DE RECRUTEMENT")
    print("Utilisant Gemini API pour la génération adaptative\n")
    
    # Décommentez la ligne suivante pour exécuter
    main()
    
    print("⚠️  ÉTAPES POUR UTILISER LE SYSTÈME:")
    print("1. 📦 Installer les dépendances: pip install google-generativeai")
    print("2. 🔑 Remplacer YOUR_API_KEY par votre vraie clé API Gemini")
    print("3. 🚀 Décommenter main() pour tester")
    print("4. 💡 Obtenir une clé API sur: https://aistudio.google.com/")
    
    print("\n🧪 Pour tester une génération simple, décommentez:")
    print("# main()")
    
    print("\n🎯 FONCTIONNALITÉS DISPONIBLES:")
    print("- test_api_connection() : Teste la connexion API")
    print("- ProfileAnalyzer(profile) : Analyse un profil CV")
    print("- QuizGenerator.generate_quiz() : Génère un quiz adaptatif") 
    print("- save_quiz_to_json() : Sauvegarde le quiz")