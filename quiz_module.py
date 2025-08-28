# quiz_module.py - Générateur de Quiz de Recrutement
import json
import google.generativeai as genai
from typing import Dict, List, Literal
from dataclasses import dataclass
from datetime import datetime

# Configuration de l'API Gemini
GEMINI_API_KEY = "AIzaSyDTuizxjEyc9WdgvIcJmONBqVPKg6A0mGE"  
genai.configure(api_key=GEMINI_API_KEY)

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
    estimated_duration: int

@dataclass
class UserAnswer:
    """Structure pour stocker les réponses de l'utilisateur"""
    question_index: int
    selected_option: int
    is_correct: bool = False

@dataclass
class QuizResults:
    """Résultats du quiz"""
    user_answers: List[UserAnswer]
    score: int
    total_questions: int
    percentage: float

class QuizGenerator:
    """Générateur de quiz simplifié - utilise directement le profil JSON"""
    
    def __init__(self, model):
        self.model = model
    
    def create_prompt_from_profile(self, user_profile: Dict, 
                                  level: Literal["débutant", "intermédiaire", "avancé"], 
                                  num_questions: int = 10) -> str:
        """
        Crée un prompt simple basé directement sur le profil JSON extrait du CV
        """
        
        # Extraction simple des informations
        name = user_profile.get('name', 'Candidat')
        skills = user_profile.get('skills', [])
        education = user_profile.get('education', [])
        experience = user_profile.get('experience', [])
        
        # Définition des niveaux
        level_descriptions = {
            "débutant": "Questions fondamentales, concepts de base, syntaxe simple",
            "intermédiaire": "Applications pratiques, résolution de problèmes moyens, intégration de concepts",
            "avancé": "Optimisation, architecture, cas complexes, bonnes pratiques avancées"
        }
        
        # Construction du prompt simple et direct
        prompt = f"""
        Vous êtes un expert en recrutement technique. Générez un quiz de {num_questions} questions pour évaluer ce candidat.

        PROFIL CANDIDAT (extrait du CV):
        - Nom: {name}
        - Compétences: {', '.join(skills)}
        - Formation: {education[0].get('degree', 'Non spécifiée') if education else 'Non spécifiée'}
        - Expérience: {len(experience)} poste(s)
        
        NIVEAU DEMANDÉ: {level.upper()}
        {level_descriptions[level]}

        INSTRUCTIONS:
        1. Créez {num_questions} questions QCM (4 options chacune)
        2. Basez-vous sur les compétences listées: {', '.join(skills)}
        3. Adaptez la difficulté au niveau {level}
        4. Variez les domaines selon les compétences du candidat
        5. Questions pratiques et théoriques mélangées

        FORMAT RÉPONSE (JSON uniquement, sans autre texte):
        {{
            "quiz_title": "Quiz {level.title()} - Évaluation Technique",
            "quiz_description": "Quiz adapté au profil de {name}",
            "estimated_duration": {int(num_questions * 1.5)},
            "questions": [
                {{
                    "id": 1,
                    "question": "Question basée sur les compétences du profil",
                    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                    "correct_answer": 0,
                    "explanation": "Explication détaillée",
                    "skill_area": "Compétence du profil concernée",
                    "difficulty": "{level}"
                }}
            ]
        }}
        """
        
        return prompt
    
    def extract_json_from_response(self, response_text: str) -> dict:
        """Extrait le JSON de la réponse"""
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
        
        # Nettoyage si nécessaire
        cleaned_text = response_text.strip()
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith('```'):
            cleaned_text = cleaned_text[:-3]
        
        return json.loads(cleaned_text.strip())
    
    def generate_quiz(self, user_profile: Dict, 
                     level: Literal["débutant", "intermédiaire", "avancé"], 
                     num_questions: int = 10) -> Quiz:
        """Génère un quiz directement à partir du profil JSON"""
        
        try:
            # Création du prompt simple
            prompt = self.create_prompt_from_profile(user_profile, level, num_questions)
            
            print(f"📡 Génération du quiz niveau {level} pour {user_profile.get('name', 'Candidat')}...")
            
            # Appel API
            response = self.model.generate_content(prompt)
            
            # Parsing JSON
            quiz_data = self.extract_json_from_response(response.text)
            
            # Création des objets Question
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
            
            print(f"✅ Quiz créé: {len(quiz.questions)} questions")
            return quiz
            
        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            return None

class QuizEvaluator:
    """Classe pour évaluer les réponses du quiz avec vérification Gemini"""
    
    def __init__(self, model=None):
        """Initialise l'évaluateur avec le modèle Gemini"""
        self.model = model or genai.GenerativeModel('gemini-1.5-flash')
    
    def verify_question_with_gemini(self, question: QuizQuestion) -> dict:
        """Vérifie une question avec Gemini pour s'assurer de la justesse"""
        
        prompt = f"""
        Vérifiez cette question de quiz et sa réponse :
        
        Question: {question.question}
        Options: {question.options}
        Réponse marquée comme correcte: {question.options[question.correct_answer]} (index {question.correct_answer})
        Explication fournie: {question.explanation}
        
        INSTRUCTIONS:
        1. Calculez ou analysez la vraie réponse correcte
        2. Vérifiez si l'index de réponse correcte est bon
        3. Vérifiez si l'explication est cohérente avec la réponse
        
        Répondez au format JSON UNIQUEMENT:
        {{
            "is_correct_answer_valid": true/false,
            "correct_answer_index": index_correct,
            "correct_option_text": "texte de la bonne réponse",
            "explanation_is_valid": true/false,
            "corrected_explanation": "explication corrigée si nécessaire",
            "verification_details": "détails de votre vérification"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Nettoyage de la réponse pour extraire le JSON
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            return json.loads(response_text)
        except Exception as e:
            print(f" Erreur lors de la vérification Gemini: {e}")
            return {
                "is_correct_answer_valid": True,
                "correct_answer_index": question.correct_answer,
                "correct_option_text": question.options[question.correct_answer],
                "explanation_is_valid": True,
                "corrected_explanation": question.explanation,
                "verification_details": "Vérification échouée, valeurs originales conservées"
            }
    
    def generate_detailed_explanation(self, question: QuizQuestion, user_answer_index: int, is_correct: bool) -> str:
        """Génère une explication détaillée avec Gemini"""
        
        user_answer = question.options[user_answer_index] if user_answer_index >= 0 else "Aucune réponse"
        correct_answer = question.options[question.correct_answer]
        
        prompt = f"""
        Générez une explication pédagogique pour cette question de quiz :
        
        Question: {question.question}
        Réponse de l'utilisateur: {user_answer}
        Réponse correcte: {correct_answer}
        Résultat: {" Correct" if is_correct else " Incorrect"}
        
        Créez une explication qui :
        1. Explique pourquoi la réponse correcte est bonne
        2. Si l'utilisateur s'est trompé, explique pourquoi sa réponse est incorrecte
        3. Donne des conseils pédagogiques
        4. Reste bienveillante et constructive
        
        Format souhaité:
         Explication: [votre explication détaillée]
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f" Erreur génération explication: {e}")
            return f" Explication: {question.explanation}"
    
    @staticmethod
    def evaluate_answers(quiz: Quiz, user_answers: Dict[int, int]) -> QuizResults:
        """Évalue les réponses de l'utilisateur avec vérification Gemini"""
        
        # Créer une instance d'évaluateur pour utiliser Gemini
        evaluator = QuizEvaluator()
        
        results = []
        score = 0
        corrections_made = 0
        
        print(" Vérification des questions avec Gemini...")
        
        for i, question in enumerate(quiz.questions):
            # Vérification de la question avec Gemini
            verification = evaluator.verify_question_with_gemini(question)
            
            # Si Gemini détecte une erreur, on corrige
            if not verification["is_correct_answer_valid"]:
                print(f" Question {i+1}: Correction détectée par Gemini")
                print(f"   Ancienne réponse: {question.options[question.correct_answer]}")
                print(f"   Nouvelle réponse: {verification['correct_option_text']}")
                
                # Mettre à jour la question
                question.correct_answer = verification["correct_answer_index"]
                if not verification["explanation_is_valid"]:
                    question.explanation = verification["corrected_explanation"]
                
                corrections_made += 1
            
            # Évaluation de la réponse utilisateur
            user_answer_index = user_answers.get(i, -1)
            is_correct = (user_answer_index == question.correct_answer)
            
            if is_correct:
                score += 1
            
            # Générer une explication détaillée
            detailed_explanation = evaluator.generate_detailed_explanation(
                question, user_answer_index, is_correct
            )
                
            results.append(UserAnswer(
                question_index=i,
                selected_option=user_answer_index,
                is_correct=is_correct
            ))
        
        percentage = (score / len(quiz.questions)) * 100 if quiz.questions else 0
        
        if corrections_made > 0:
            print(f" {corrections_made} question(s) corrigée(s) automatiquement par Gemini")
        
        return QuizResults(
            user_answers=results,
            score=score,
            total_questions=len(quiz.questions),
            percentage=percentage
        )
    
    def display_detailed_results(self, quiz: Quiz, results: QuizResults, user_answers: Dict[int, int]):
        """Affiche les résultats détaillés avec explications Gemini"""
        
        print("=" * 80)
        print(f" RÉSULTATS DU QUIZ: {quiz.title}")
        print(f"Score: {results.score}/{results.total_questions} ({results.percentage:.1f}%)")
        print("=" * 80)
        
        for i, (question, result) in enumerate(zip(quiz.questions, results.user_answers)):
            print(f"\n Question {i+1}: {question.question}")
            
            # Affichage des options avec marquage
            for j, option in enumerate(question.options):
                marker = ""
                if j == question.correct_answer:
                    marker = " ✅"
                elif j == result.selected_option:
                    marker = " ❌" if not result.is_correct else " ✅"
                
                print(f"   {option}{marker}")
            
            # Résultat
            if result.is_correct:
                print("🎉 Votre réponse est CORRECTE !")
            else:
                user_answer = question.options[result.selected_option] if result.selected_option >= 0 else "Aucune réponse"
                print(f"❌ Votre réponse: {user_answer}")
                print(f"✅ Réponse correcte: {question.options[question.correct_answer]}")
            
            # Explication détaillée générée par Gemini
            detailed_explanation = self.generate_detailed_explanation(
                question, result.selected_option, result.is_correct
            )
            print(detailed_explanation)
            print("-" * 60)

def display_quiz(quiz: Quiz):
    """Affiche le quiz"""
    if not quiz:
        print("❌ Aucun quiz à afficher")
        return
    
    print("=" * 60)
    print(f"🎯 {quiz.title}")
    print(f"📋 {quiz.description}")
    print(f"⏱️  Durée: {quiz.estimated_duration} minutes")
    print("=" * 60)
    
    for i, question in enumerate(quiz.questions, 1):
        print(f"\n❓ Question {i}: {question.question}")
        print(f"🎯 Compétence: {question.skill_area}")
        
        for option in question.options:
            print(f"   {option}")
        
        print(f"✅ Réponse: {question.options[question.correct_answer]}")
        print(f"💡 {question.explanation}")
        print("-" * 40)

def save_quiz_to_json(quiz: Quiz, filename: str) -> bool:
    """Sauvegarde le quiz"""
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