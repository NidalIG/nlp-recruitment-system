import streamlit as st
from quiz_module import ProfileAnalyzer, QuizGenerator, model, user_profile

st.title("🎓 Générateur de Quiz de Recrutement")

# Sélecteur du niveau
niveau = st.selectbox(
    "Choisissez le niveau du quiz :",
    options=["débutant", "intermédiaire", "avancé"],
    index=1  # "intermédiaire" par défaut
)

if st.button("Analyser le profil et générer le quiz"):
    analyzer = ProfileAnalyzer(user_profile)
    st.subheader("🔍 Analyse du profil")
    st.write(f"Nom: {analyzer.profile['name']}")
    st.write(f"Compétences principales: {analyzer.get_primary_skills()[:5]}")
    st.write(f"Domaines de focus: {analyzer.get_domain_focus()}")
    st.write(f"Niveau d'expérience estimé: {analyzer.get_experience_level()}")

    generator = QuizGenerator(model)
    quiz = generator.generate_quiz(analyzer, niveau, num_questions=10)

    if quiz:
        st.subheader(f"🚀 Quiz généré: {quiz.title}")
        st.write(f"Description: {quiz.description}")
        st.write(f"Niveau: {quiz.level}")
        for i, q in enumerate(quiz.questions, 1):
            st.markdown(f"**Q{i}: {q.question}**")
            for opt in q.options:
                st.write(opt)
            st.write(f"**Réponse correcte:** {q.options[q.correct_answer]}")
            st.caption(f"💡 {q.explanation}")
    else:
        st.error("Échec de la génération du quiz.")
