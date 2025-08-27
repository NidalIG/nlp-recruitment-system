# quiz_module.py - Générateur de Quiz de Recrutement
import json
import google.generativeai as genai
from typing import Dict, List, Literal
from dataclasses import dataclass
from datetime import datetime

# Configuration de l'API Gemini
GEMINI_API_KEY = "AIzaSyCGScegfQ9kF4zcLErYf3cTFE9XTa_v1Pw"  
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
    """Classe pour évaluer les réponses du quiz"""
    
    @staticmethod
    def evaluate_answers(quiz: Quiz, user_answers: Dict[int, int]) -> QuizResults:
        """Évalue les réponses de l'utilisateur"""
        results = []
        score = 0
        
        for i, question in enumerate(quiz.questions):
            user_answer_index = user_answers.get(i, -1)
            is_correct = (user_answer_index == question.correct_answer)
            
            if is_correct:
                score += 1
                
            results.append(UserAnswer(
                question_index=i,
                selected_option=user_answer_index,
                is_correct=is_correct
            ))
        
        percentage = (score / len(quiz.questions)) * 100 if quiz.questions else 0
        
        return QuizResults(
            user_answers=results,
            score=score,
            total_questions=len(quiz.questions),
            percentage=percentage
        )

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