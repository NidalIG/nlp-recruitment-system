# quiz_module.py - Générateur de Quiz de Recrutement (amélioré)
# - Support de focus_skills (cibler des compétences clés)
# - Extraction JSON robuste depuis les réponses Gemini
# - Validation/normalisation des questions (4 options, index correct, trimming)
# - Prompts cadrés (sortie JSON only) + contrôle du niveau
# - Évaluateur plus résilient (fallbacks en cas d'échec de parsing)

from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Literal, Optional, Any

import google.generativeai as genai
from dotenv import load_dotenv

# ======================================================================
# Configuration Gemini
# ======================================================================
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

DEFAULT_GENERATION_CONFIG = {
    "temperature": 0.6,
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 2048,
}

# Modèle par défaut (utilisé si aucun modèle n'est injecté)
_default_model = genai.GenerativeModel(
    "gemini-1.5-flash",
    generation_config=DEFAULT_GENERATION_CONFIG,
)

# ======================================================================
# Dataclasses
# ======================================================================
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

# ======================================================================
# Helpers internes
# ======================================================================
_LEVEL_DESCRIPTIONS = {
    "débutant": "Questions fondamentales, concepts de base et définitions clés.",
    "intermédiaire": "Applications pratiques, résolution de problèmes courants, intégration de concepts.",
    "avancé": "Optimisation, architecture, complexité, bonnes pratiques avancées et cas réels.",
}

def _norm_level(level: str) -> str:
    level = (level or "").lower()
    if level not in _LEVEL_DESCRIPTIONS:
        return "intermédiaire"
    return level

def _strip_choice_prefix(opt: str) -> str:
    """Retire les préfixes A) / B) ... si présents, et trim."""
    if not isinstance(opt, str):
        return str(opt)
    s = opt.strip()
    # Ex: "A) foo", "A. foo", "A - foo"
    s = re.sub(r"^[A-Da-d]\s*[\)\.\-]\s*", "", s).strip()
    return s

def _unique_preserve_order(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out

def _safe_json_extract(text: str) -> dict:
    """
    Tente d'extraire un JSON valide à partir d'un texte (gère les fences, le blabla autour).
    Lève ValueError en cas d'échec.
    """
    if not text:
        raise ValueError("Réponse vide")

    t = text.strip()
    # Retirer fences ```json ... ``` ou ``` ... ```
    if t.startswith("```json"):
        t = t[7:]
        if t.endswith("```"):
            t = t[:-3]
    elif t.startswith("```"):
        t = t[3:]
        if t.endswith("```"):
            t = t[:-3]
    t = t.strip()

    # Heuristique: si ça ne commence/termine pas par { }, essayer de découper
    if not (t.startswith("{") and t.endswith("}")):
        start = t.find("{")
        end = t.rfind("}")
        if start != -1 and end != -1 and end > start:
            t = t[start:end + 1]

    try:
        return json.loads(t)
    except json.JSONDecodeError:
        # Dernier essai: enlever des lignes de tête/pied parasites
        lines = [ln for ln in t.splitlines() if ln.strip()]
        joined = "\n".join(lines)
        # Trouver premier { et dernier }
        start = joined.find("{")
        end = joined.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = joined[start:end + 1]
            return json.loads(candidate)
        raise

def _validate_and_fix_question(q: Dict[str, Any], default_level: str) -> QuizQuestion:
    """
    Valide/normalise une question issue du JSON.
    - Garantit 4 options max (ou pad), supprime doublons, retire préfixes "A) " etc.
    - Corrige correct_answer out-of-range.
    """
    question = str(q.get("question", "")).strip()
    options_raw = q.get("options", []) or []
    explanation = str(q.get("explanation", "")).strip() or "Voir la réponse correcte."
    skill_area = str(q.get("skill_area", "Général")).strip() or "Général"
    difficulty = str(q.get("difficulty", default_level)).strip() or default_level

    # Nettoyage et déduplication des options
    options = [_strip_choice_prefix(str(o)) for o in options_raw if str(o).strip()]
    options = _unique_preserve_order(options)

    # Trim à 4 options max
    if len(options) > 4:
        options = options[:4]

    # Si insuffisant, pad avec des placeholders
    while len(options) < 4:
        options.append(f"Option {len(options)+1}")

    # Index de la bonne réponse
    try:
        answer_index = int(q.get("correct_answer", 0))
    except Exception:
        answer_index = 0

    # Clamp dans la plage
    if answer_index < 0 or answer_index >= len(options):
        answer_index = 0

    return QuizQuestion(
        question=question or "Question",
        options=options,
        correct_answer=answer_index,
        explanation=explanation,
        skill_area=skill_area,
        difficulty=difficulty
    )

def _build_quiz_from_json(quiz_data: Dict[str, Any], level: str) -> Quiz:
    """Construit l'objet Quiz complet à partir du JSON Gemini + validations."""
    title = str(quiz_data.get("quiz_title", f"Quiz {level.title()} - Évaluation Technique")).strip()
    desc = str(quiz_data.get("quiz_description", "Quiz généré automatiquement à partir du profil.")).strip()
    est = int(quiz_data.get("estimated_duration", 15))

    raw_questions = quiz_data.get("questions", []) or []
    questions: List[QuizQuestion] = [_validate_and_fix_question(q, level) for q in raw_questions]

    # Si aucune question valide, on ajoute une question placeholder
    if not questions:
        questions = [
            QuizQuestion(
                question="Placeholder: question indisponible.",
                options=["Option 1", "Option 2", "Option 3", "Option 4"],
                correct_answer=0,
                explanation="Aucune donnée valide reçue du modèle.",
                skill_area="Général",
                difficulty=level,
            )
        ]

    return Quiz(
        title=title,
        description=desc,
        level=level,
        questions=questions,
        estimated_duration=est,
    )

# ======================================================================
# Générateur de quiz
# ======================================================================
class QuizGenerator:
    """Générateur de quiz basé sur profil JSON (CV parsé) et compétences ciblées."""

    def __init__(self, model: Optional[genai.GenerativeModel] = None):
        self.model = model or _default_model

    def create_prompt_from_profile(
        self,
        user_profile: Dict[str, Any],
        level: Literal["débutant", "intermédiaire", "avancé"],
        num_questions: int = 10,
        focus_skills: Optional[List[str]] = None,
    ) -> str:
        """
        Crée un prompt strict (sortie JSON uniquement) basé sur le profil.
        focus_skills : compétences à privilégier (ex: issues du dernier matching).
        """

        name = user_profile.get("name", "Candidat")
        skills = [str(s).strip() for s in (user_profile.get("skills", []) or []) if str(s).strip()]
        education = user_profile.get("education", [])
        experience = user_profile.get("experience", [])
        first_degree = (
            education[0].get("degree", "Non spécifiée") if education and isinstance(education[0], dict) else "Non spécifiée"
        )
        level = _norm_level(level)

        focus_skills = [s for s in (focus_skills or []) if isinstance(s, str) and s.strip()]
        focus_block = ""
        distribution_rule = ""
        if focus_skills:
            # Règle simple: ~60% des questions sur les focus_skills (arrondi)
            n_focus = max(1, round(num_questions * 0.6))
            focus_csv = ", ".join(focus_skills)
            focus_block = f"\nCOMPÉTENCES PRIORITAIRES À COUVRIR (~{n_focus}/{num_questions}): {focus_csv}"
            distribution_rule = (
                f"   - Couvrez PRIORITAIREMENT ces compétences (environ {n_focus} questions sur {num_questions}).\n"
                f"   - Les autres questions peuvent couvrir les compétences du profil pertinentes."
            )

        prompt = f"""
Tu es un recruteur technique. GÉNÈRE EXCLUSIVEMENT DU JSON VALIDE (AUCUN TEXTE EN DEHORS DU JSON).

PROFIL CANDIDAT (extrait du CV):
- Nom: {name}
- Compétences: {", ".join(skills) if skills else "Non spécifiées"}
- Formation principale: {first_degree}
- Nombre d'expériences: {len(experience)}
{focus_block}

NIVEAU DEMANDÉ: {level.upper()}
{_LEVEL_DESCRIPTIONS[level]}

CONTRAINTES DE GÉNÉRATION:
1. Génère exactement {num_questions} questions QCM avec 4 options chacune (ni plus, ni moins).
2. Les options doivent être des chaînes simples. Évite les suffixes techniques inutiles.
3. La clé "correct_answer" doit être l'INDEX (0..3) de la bonne option.
4. Varie théorie/pratique, avec un langage clair et concis.
5. Utilise le FRANÇAIS.
6. Chaque question doit cibler une 'skill_area' explicite (ex: 'Python', 'Cloud', 'SQL', etc.).
7. Respecte STRICTEMENT le format JSON demandé ci-dessous. PAS DE TEXTE HORS JSON.
{distribution_rule if distribution_rule else ""}

FORMAT JSON EXACT À PRODUIRE (ne mets aucun commentaire):
{{
  "quiz_title": "Quiz {level.title()} - Évaluation Technique",
  "quiz_description": "Quiz adapté au profil de {name}",
  "estimated_duration": {int(num_questions * 1.5)},
  "questions": [
    {{
      "id": 1,
      "question": "Question basée sur les compétences du profil",
      "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
      "correct_answer": 0,
      "explanation": "Explication concise et pédagogique",
      "skill_area": "Compétence du profil concernée",
      "difficulty": "{level}"
    }}
  ]
}}
""".strip()

        return prompt

    def extract_json_from_response(self, response_text: str) -> dict:
        """Extrait le JSON de la réponse (robuste)."""
        return _safe_json_extract(response_text)

    def generate_quiz(
        self,
        user_profile: Dict[str, Any],
        level: Literal["débutant", "intermédiaire", "avancé"],
        num_questions: int = 10,
        focus_skills: Optional[List[str]] = None,
    ) -> Optional[Quiz]:
        """Génère un quiz depuis le profil JSON + focus_skills éventuels."""
        try:
            level = _norm_level(level)
            prompt = self.create_prompt_from_profile(
                user_profile=user_profile,
                level=level,
                num_questions=num_questions,
                focus_skills=focus_skills,
            )

            print(f"📡 Génération du quiz ({num_questions} q) niveau {level}"
                  f"{' | focus=' + ','.join(focus_skills) if focus_skills else ''}"
                  f" pour {user_profile.get('name', 'Candidat')}...")

            response = self.model.generate_content(prompt)
            raw_text = (response.text or "").strip()
            quiz_data = self.extract_json_from_response(raw_text)
            quiz = _build_quiz_from_json(quiz_data, level)
            print(f"✅ Quiz créé: {len(quiz.questions)} question(s)")
            return quiz

        except Exception as e:
            print(f"❌ Erreur génération quiz: {str(e)}")
            return None

# ======================================================================
# Évaluateur de quiz
# ======================================================================
class QuizEvaluator:
    """Évalue les réponses du quiz, avec vérification Gemini plus robuste."""

    def __init__(self, model: Optional[genai.GenerativeModel] = None):
        self.model = model or _default_model

    def _verify_question_json(self, txt: str) -> dict:
        """Extrait un JSON pour la vérification de réponse."""
        data = _safe_json_extract(txt)
        # Normalisation minimale des champs attendus
        return {
            "is_correct_answer_valid": bool(data.get("is_correct_answer_valid", True)),
            "correct_answer_index": int(data.get("correct_answer_index", 0)),
            "correct_option_text": str(data.get("correct_option_text", "")),
            "explanation_is_valid": bool(data.get("explanation_is_valid", True)),
            "corrected_explanation": str(data.get("corrected_explanation", "")),
            "verification_details": str(data.get("verification_details", "")),
        }

    def verify_question_with_gemini(self, question: QuizQuestion) -> dict:
        """Vérifie une question (cohérence de la réponse & explication)."""
        prompt = f"""
Vérifie la cohérence de cette question de quiz (réponds UNIQUEMENT en JSON valide):

Question: {question.question}
Options: {question.options}
Index de la réponse marquée comme correcte: {question.correct_answer}
Texte de la réponse marquée: {question.options[question.correct_answer] if 0 <= question.correct_answer < len(question.options) else '' }
Explication: {question.explanation}

INSTRUCTIONS DE VÉRIFICATION:
- Calcule la vraie réponse correcte (index 0..3).
- Compare avec l'index fourni.
- Indique si l'explication est cohérente, sinon propose une version corrigée et concise.

FORMAT JSON:
{{
  "is_correct_answer_valid": true,
  "correct_answer_index": 0,
  "correct_option_text": "texte de la bonne réponse",
  "explanation_is_valid": true,
  "corrected_explanation": "explication corrigée si nécessaire",
  "verification_details": "brefs détails de vérification"
}}
""".strip()

        try:
            resp = self.model.generate_content(prompt)
            return self._verify_question_json(resp.text or "")
        except Exception as e:
            print(f"⚠️  Erreur vérification Gemini: {e}")
            # Fallback: on conserve la question telle quelle
            return {
                "is_correct_answer_valid": True,
                "correct_answer_index": question.correct_answer,
                "correct_option_text": question.options[question.correct_answer]
                if 0 <= question.correct_answer < len(question.options) else "",
                "explanation_is_valid": True,
                "corrected_explanation": question.explanation,
                "verification_details": "Vérification échouée, valeurs originales conservées",
            }

    def generate_detailed_explanation(self, question: QuizQuestion, user_answer_index: int, is_correct: bool) -> str:
        """Génère une explication pédagogique simple."""
        user_answer = (
            question.options[user_answer_index] if 0 <= user_answer_index < len(question.options) else "Aucune réponse"
        )
        correct_answer = question.options[question.correct_answer]

        prompt = f"""
Génère une explication pédagogique en FRANÇAIS pour cette question.
- Courte (2-4 phrases), bienveillante, actionable.

Question: {question.question}
Réponse de l'utilisateur: {user_answer}
Réponse correcte: {correct_answer}
Résultat: {"Correct" if is_correct else "Incorrect"}

Format de sortie: une explication en texte brut (pas de JSON).
""".strip()

        try:
            resp = self.model.generate_content(prompt)
            return (resp.text or "").strip() or question.explanation
        except Exception:
            return question.explanation

    @staticmethod
    def evaluate_answers(quiz: Quiz, user_answers: Dict[int, int]) -> QuizResults:
        """Évalue les réponses de l'utilisateur, avec vérification/correction automatique."""
        evaluator = QuizEvaluator()
        results: List[UserAnswer] = []
        score = 0
        corrections_made = 0

        print("🔎 Vérification des questions avec Gemini...")

        for i, question in enumerate(quiz.questions):
            # Vérification/correction
            verification = evaluator.verify_question_with_gemini(question)
            if not verification.get("is_correct_answer_valid", True):
                new_idx = int(verification.get("correct_answer_index", question.correct_answer))
                if 0 <= new_idx < len(question.options):
                    print(f"🛠️  Question {i+1}: correction de la bonne réponse ({question.correct_answer} -> {new_idx})")
                    question.correct_answer = new_idx
                    corrections_made += 1

                if not verification.get("explanation_is_valid", True):
                    corrected = verification.get("corrected_explanation", "").strip()
                    if corrected:
                        question.explanation = corrected

            # Évaluation de la réponse utilisateur
            user_answer_index = int(user_answers.get(i, -1))
            is_correct = (user_answer_index == question.correct_answer)
            if is_correct:
                score += 1

            results.append(UserAnswer(
                question_index=i,
                selected_option=user_answer_index,
                is_correct=is_correct
            ))

        if corrections_made:
            print(f"ℹ️  {corrections_made} question(s) corrigée(s) automatiquement.")

        percentage = (score / len(quiz.questions)) * 100 if quiz.questions else 0.0
        return QuizResults(
            user_answers=results,
            score=score,
            total_questions=len(quiz.questions),
            percentage=percentage
        )

    def display_detailed_results(self, quiz: Quiz, results: QuizResults, user_answers: Dict[int, int]):
        """Affiche des résultats détaillés (utile en mode CLI/local)."""
        print("=" * 80)
        print(f" RÉSULTATS DU QUIZ: {quiz.title}")
        print(f"Score: {results.score}/{results.total_questions} ({results.percentage:.1f}%)")
        print("=" * 80)

        for i, (question, result) in enumerate(zip(quiz.questions, results.user_answers)):
            print(f"\n Question {i+1}: {question.question}")
            for j, option in enumerate(question.options):
                marker = ""
                if j == question.correct_answer:
                    marker = " ✅"
                elif j == result.selected_option:
                    marker = " ❌" if not result.is_correct else " ✅"
                print(f"   {option}{marker}")

            if result.is_correct:
                print("🎉 Votre réponse est CORRECTE !")
            else:
                ua = question.options[result.selected_option] if 0 <= result.selected_option < len(question.options) else "Aucune réponse"
                print(f"❌ Votre réponse: {ua}")
                print(f"✅ Réponse correcte: {question.options[question.correct_answer]}")

            detailed = self.generate_detailed_explanation(question, result.selected_option, result.is_correct)
            print(detailed)
            print("-" * 60)

# ======================================================================
# Utilitaires d'affichage/sauvegarde (facultatifs pour votre backend)
# ======================================================================
def display_quiz(quiz: Optional[Quiz]):
    """Affiche un quiz en console (debug/local)."""
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

def save_quiz_to_json(quiz: Optional[Quiz], filename: str) -> bool:
    """Sauvegarde un quiz au format JSON (utilitaire)."""
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
                "difficulty": q.difficulty,
            }
            for q in quiz.questions
        ],
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(quiz_dict, f, ensure_ascii=False, indent=2)
    return True
