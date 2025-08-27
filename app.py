import streamlit as st
import json
from quiz_module import QuizGenerator, model, QuizEvaluator, QuizResults, UserAnswer

st.title("🎓 Générateur de Quiz - Adaptatif au Profil CV")

# Initialisation des états de session
if 'quiz' not in st.session_state:
    st.session_state.quiz = None
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'quiz_submitted' not in st.session_state:
    st.session_state.quiz_submitted = False
if 'quiz_results' not in st.session_state:
    st.session_state.quiz_results = None

# PROFIL JSON (normalement fourni par votre système de parsing CV)
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

# Interface simple
st.subheader("👤 Profil candidat")
col1, col2 = st.columns(2)

with col1:
    st.write(f"**Nom:** {user_profile['name']}")
    st.write(f"**Email:** {user_profile['email']}")
    if user_profile['education']:
        st.write(f"**Formation:** {user_profile['education'][0]['degree']}")

with col2:
    st.write(f"**Compétences:** {len(user_profile['skills'])}")
    st.write(f"**Expérience:** {len(user_profile['experience'])} poste(s)")

# Configuration du quiz
st.subheader("⚙️ Configuration du Quiz")

col_config1, col_config2 = st.columns(2)

with col_config1:
    niveau = st.selectbox(
        "Niveau de difficulté:",
        options=["débutant", "intermédiaire", "avancé"],
        index=1
    )

with col_config2:
    nb_questions = st.slider("Nombre de questions:", 5, 20, 10)

# Génération
if st.button("🚀 Générer le Quiz Adaptatif", type="primary"):
    
    with st.spinner(f"Génération de {nb_questions} questions niveau {niveau}..."):
        
        # Création du générateur
        generator = QuizGenerator(model)
        
        # Génération du quiz directement depuis le profil JSON
        quiz = generator.generate_quiz(
            user_profile=user_profile,
            level=niveau,
            num_questions=nb_questions
        )
        
        if quiz:
            st.session_state.quiz = quiz
            st.session_state.user_answers = {}
            st.session_state.quiz_submitted = False
            st.session_state.quiz_results = None
            st.success("✅ Quiz généré avec succès !")
            st.rerun()
        else:
            st.error("❌ Erreur lors de la génération du quiz")

# Afficher le quiz si disponible
if st.session_state.quiz and not st.session_state.quiz_submitted:
    quiz = st.session_state.quiz
    
    st.subheader(f"🎯 {quiz.title}")
    st.write(f"**Description:** {quiz.description}")
    
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Questions", len(quiz.questions))
    with col_info2:
        st.metric("Niveau", quiz.level.title())
    with col_info3:
        st.metric("Durée estimée", f"{quiz.estimated_duration} min")
    
    # Formulaire pour le quiz
    with st.form("quiz_form"):
        st.subheader("📝 Questions du Quiz")
        
        for i, q in enumerate(quiz.questions):
            st.markdown(f"**Question {i+1}:** {q.question}")
            st.caption(f"Compétence évaluée: {q.skill_area}")
            
            # Options avec radio buttons
            options_key = f"q_{i}"
            selected_option = st.radio(
                f"Sélectionnez une réponse pour la question {i+1}:",
                options=q.options,
                index=None,
                key=options_key
            )
            
            # Stocker la réponse
            if selected_option:
                selected_index = q.options.index(selected_option)
                st.session_state.user_answers[i] = selected_index
        
        # Bouton de soumission
        submitted = st.form_submit_button("📤 Soumettre le quiz")
        
        if submitted:
            if len(st.session_state.user_answers) == len(quiz.questions):
                # Évaluation des réponses
                evaluator = QuizEvaluator()
                results = evaluator.evaluate_answers(quiz, st.session_state.user_answers)
                st.session_state.quiz_results = results
                st.session_state.quiz_submitted = True
                st.rerun()
            else:
                st.warning("Veuillez répondre à toutes les questions avant de soumettre.")

# Afficher les résultats si le quiz a été soumis
if st.session_state.quiz_submitted and st.session_state.quiz_results:
    results = st.session_state.quiz_results
    quiz = st.session_state.quiz
    
    st.subheader("📊 Résultats du Quiz")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score", f"{results.score}/{results.total_questions}")
    with col2:
        st.metric("Pourcentage", f"{results.percentage:.1f}%")
    with col3:
        performance = "Excellent" if results.percentage >= 80 else "Bon" if results.percentage >= 60 else "Moyen" if results.percentage >= 40 else "Faible"
        st.metric("Performance", performance)
    
    # Détails des réponses
    st.subheader("📝 Détail des réponses")
    
    for i, user_answer in enumerate(results.user_answers):
        q = quiz.questions[i]
        
        with st.expander(f"Question {i+1}: {q.question[:50]}...", expanded=False):
            st.markdown(f"**{q.question}**")
            
            # Afficher les options avec coloration
            for j, option in enumerate(q.options):
                if j == user_answer.selected_option and j == q.correct_answer:
                    st.success(f"✅ {option} (Votre réponse - Correcte)")
                elif j == user_answer.selected_option:
                    st.error(f"❌ {option} (Votre réponse - Incorrecte)")
                elif j == q.correct_answer:
                    st.success(f"✅ {option} (Réponse correcte)")
                else:
                    st.write(f"• {option}")
            
            st.info(f"💡 **Explication:** {q.explanation}")
    
    # Bouton pour recommencer
    if st.button("🔄 Générer un nouveau quiz"):
        st.session_state.quiz = None
        st.session_state.user_answers = {}
        st.session_state.quiz_submitted = False
        st.session_state.quiz_results = None
        st.rerun()

# Sidebar avec informations
st.sidebar.title("ℹ️ Comment ça marche")
st.sidebar.write("""
**1. Profil JSON** 
Le système utilise directement le profil JSON extrait de votre parsing de CV.

**2. Adaptation automatique**
Les questions sont générées selon:
- Vos compétences réelles
- Le niveau choisi
- Votre formation et expérience

**3. Génération intelligente**
L'IA Gemini adapte automatiquement:
- Le type de questions
- La difficulté
- Les domaines techniques
""")

# Test de l'API
if st.sidebar.button("🔧 Tester l'API"):
    try:
        response = model.generate_content("Test API: répondez 'OK'")
        st.sidebar.success("✅ API Gemini connectée")
        st.sidebar.code(response.text[:100] + "...")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur API: {str(e)}")

# Information sur le profil actuel
st.sidebar.title("👤 Profil actuel")
st.sidebar.write(f"**{user_profile['name']}**")
st.sidebar.write(f"Compétences: {len(user_profile['skills'])}")

# Footer
st.markdown("---")
st.caption("🎓 Générateur de Quiz Adaptatif - Utilise l'API Gemini pour créer des questions personnalisées selon votre profil CV")