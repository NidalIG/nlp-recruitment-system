 
import numpy as np
from typing import Dict, List, Optional

# Embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️ sentence-transformers non installé. Utilisez: pip install sentence-transformers")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ openai non installé pour les embeddings GPT. Utilisez: pip install openai")

try:
    import torch
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️ transformers non installé. Utilisez: pip install transformers torch")


class CVJobEmbeddingSimilarity:
    def __init__(self, model_type: str = "sentence_transformer"):
        """
        model_type options:
        - "sentence_transformer": Utilise SentenceTransformer (recommandé)
        - "openai": Utilise OpenAI embeddings (nécessite API key)
        - "camembert": Utilise CamemBERT (français)
        """
        self.model_type = model_type
        self.model = None
        self.tokenizer = None
        self._load_model()
        self.weights = {
            'global_similarity': 0.4,
            'skills_similarity': 0.35,
            'experience_similarity': 0.15,
            'education_similarity': 0.1
        }

    def _load_model(self):
        if self.model_type == "sentence_transformer" and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer('distiluse-base-multilingual-cased')
                print("✅ SentenceTransformer chargé")
            except:
                print("❌ Impossible de charger SentenceTransformer")
        elif self.model_type == "camembert" and TRANSFORMERS_AVAILABLE:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained("camembert-base")
                self.model = AutoModel.from_pretrained("camembert-base")
                print("✅ CamemBERT chargé")
            except:
                print("❌ Impossible de charger CamemBERT")
        elif self.model_type == "openai" and OPENAI_AVAILABLE:
            print("✅ OpenAI embeddings prêt (vérifier OPENAI_API_KEY)")
        else:
            print("❌ Modèle non disponible ou dépendances manquantes")

    def extract_sections_from_cv(self, cv_data: Dict) -> Dict[str, str]:
        sections = {}
        sections['skills'] = ' '.join(cv_data.get('skills', []))
        experience_texts = [f"{exp.get('job_title','')} {exp.get('description','')}" for exp in cv_data.get('experience', [])]
        sections['experience'] = ' '.join(experience_texts)
        education_texts = [f"{edu.get('degree','')} {edu.get('institution_name','')}" for edu in cv_data.get('education', [])]
        sections['education'] = ' '.join(education_texts)
        sections['certifications'] = ' '.join(cv_data.get('certifications', []))
        sections['global'] = ' '.join(filter(None, [sections.get(k, '') for k in sections]))
        return sections

    def extract_sections_from_job(self, job_data: Dict) -> Dict[str, str]:
        sections = {}
        if 'required_skills' in job_data:
            sections['skills'] = ' '.join(job_data['required_skills']) if isinstance(job_data['required_skills'], list) else job_data['required_skills']
        sections['experience'] = job_data.get('experience_required', '')
        sections['education'] = job_data.get('education_required', '')
        sections['global'] = ' '.join(filter(None, [
            job_data.get('title', ''),
            job_data.get('description', ''),
            sections.get('skills', ''),
            sections.get('experience', ''),
            sections.get('education', '')
        ]))
        return sections

    def get_sentence_transformer_embeddings(self, texts: List[str]) -> np.ndarray:
        cleaned_texts = [t.strip() for t in texts if t.strip()]
        if not cleaned_texts:
            return np.array([])
        return self.model.encode(cleaned_texts, convert_to_tensor=False)

    def get_camembert_embeddings(self, texts: List[str]) -> np.ndarray:
        embeddings = []
        for text in texts:
            if not text.strip():
                continue
            inputs = self.tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
            with torch.no_grad():
                outputs = self.model(**inputs)
                embeddings.append(outputs.last_hidden_state.mean(dim=1).squeeze().numpy())
        return np.array(embeddings) if embeddings else np.array([])

    def get_openai_embeddings(self, texts: List[str], model="text-embedding-3-small") -> np.ndarray:
        embeddings = []
        for text in texts:
            if not text.strip():
                continue
            try:
                response = openai.embeddings.create(input=text, model=model)
                embeddings.append(response.data[0].embedding)
            except:
                embeddings.append(np.random.randn(1536))
        return np.array(embeddings) if embeddings else np.array([])

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        if self.model_type == "sentence_transformer":
            return self.get_sentence_transformer_embeddings(texts)
        if self.model_type == "camembert":
            return self.get_camembert_embeddings(texts)
        if self.model_type == "openai":
            return self.get_openai_embeddings(texts)
        raise ValueError(f"Modèle non supporté: {self.model_type}")

    def calculate_sectional_similarity(self, cv_data: Dict, job_data: Dict) -> Dict:
        from sklearn.metrics.pairwise import cosine_similarity
        cv_sections = self.extract_sections_from_cv(cv_data)
        job_sections = self.extract_sections_from_job(job_data)
        similarities = {}
        for section in ['skills', 'experience', 'education', 'global']:
            cv_text, job_text = cv_sections.get(section, ''), job_sections.get(section, '')
            if not cv_text or not job_text:
                similarities[section] = 0.0
                continue
            try:
                embeddings = self.generate_embeddings([cv_text, job_text])
                if len(embeddings) == 2:
                    sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
                    similarities[section] = float(max(0, sim))
                else:
                    similarities[section] = 0.0
            except:
                similarities[section] = 0.0
        return similarities

    def calculate_skill_embedding_similarity(self, cv_skills: List[str], job_skills: List[str]) -> Dict:
        from sklearn.metrics.pairwise import cosine_similarity
        if not cv_skills or not job_skills:
            return {'average_similarity': 0.0, 'max_similarity': 0.0, 'skill_matches': [], 'coverage': 0.0}
        all_skills = cv_skills + job_skills
        embeddings = self.generate_embeddings(all_skills)
        if len(embeddings) != len(all_skills):
            return {'average_similarity': 0.0, 'max_similarity': 0.0, 'skill_matches': [], 'coverage': 0.0}
        cv_emb, job_emb = embeddings[:len(cv_skills)], embeddings[len(cv_skills):]
        sim_matrix = cosine_similarity(job_emb, cv_emb)
        skill_matches, sims = [], []
        for i, job_skill in enumerate(job_skills):
            best_idx = np.argmax(sim_matrix[i])
            best_sim = sim_matrix[i][best_idx]
            skill_matches.append({
                'job_skill': job_skill,
                'matched_cv_skill': cv_skills[best_idx],
                'similarity': float(best_sim)
            })
            sims.append(best_sim)
        average_sim = float(np.mean(sims)) if sims else 0.0
        max_sim = float(np.max(sims)) if sims else 0.0
        threshold = 0.7
        coverage = float(sum(1 for s in sims if s > threshold) / len(job_skills))
        return {
            'average_similarity': average_sim,
            'max_similarity': max_sim,
            'skill_matches': skill_matches,
            'coverage': coverage,
            'similarity_matrix': sim_matrix.tolist()
        }

    def calculate_comprehensive_embedding_similarity(self, cv_data: Dict, job_data: Dict) -> Dict:
        sectional_sim = self.calculate_sectional_similarity(cv_data, job_data)
        skill_analysis = self.calculate_skill_embedding_similarity(cv_data.get('skills', []), job_data.get('required_skills', []))
        composite_score = (sectional_sim.get('global', 0) * self.weights['global_similarity'] +
                           skill_analysis.get('average_similarity', 0) * self.weights['skills_similarity'] +
                           sectional_sim.get('experience', 0) * self.weights['experience_similarity'] +
                           sectional_sim.get('education', 0) * self.weights['education_similarity'])
        score_pct = composite_score * 100
        if score_pct >= 85:
            level = "Excellente"
        elif score_pct >= 70:
            level = "Très bonne"
        elif score_pct >= 55:
            level = "Bonne"
        elif score_pct >= 40:
            level = "Modérée"
        else:
            level = "Faible"
        return {
            'overall_similarity_score': round(score_pct, 2),
            'similarity_level': level,
            'model_used': self.model_type,
            'sectional_scores': {k: round(v * 100, 2) for k, v in sectional_sim.items()},
            'skill_analysis': {
                'average_skill_similarity': round(skill_analysis.get('average_similarity', 0) * 100, 2),
                'skill_coverage': round(skill_analysis.get('coverage', 0) * 100, 2),
                'top_skill_matches': skill_analysis.get('skill_matches', [])[:5]
            },
            'weights_applied': self.weights
        }

    def generate_detailed_report(self, cv_data: Dict, job_data: Dict) -> str:
        result = self.calculate_comprehensive_embedding_similarity(cv_data, job_data)
        report = f"""
=== RAPPORT DE SIMILARITÉ ===
Score global: {result['overall_similarity_score']}% ({result['similarity_level']})
Modèle utilisé: {result['model_used']}

Scores par section:
- Global: {result['sectional_scores']['global']}%
- Skills: {result['sectional_scores']['skills']}%
- Experience: {result['sectional_scores']['experience']}%
- Education: {result['sectional_scores']['education']}%

Top correspondances de compétences:"""
        for match in result['skill_analysis']['top_skill_matches']:
            report += f"\n- {match['job_skill']} → {match['matched_cv_skill']} ({match['similarity'] * 100:.1f}%)"
        return report.strip()


# Exemple d'utilisation
if __name__ == "__main__":
    # cv_data = {
    #     "skills": ["Python", "SQL", "Machine Learning"],
    #     "education": [{"degree": "Master AI", "institution_name": "FSTG"}],
    #     "experience": [{"job_title": "Data Scientist", "description": "Analyse de données"}],
    #     "certifications": ["AI Fundamentals"]
    # }
    # job_data = {
    #     "title": "Data Scientist",
    #     "description": "Analyse de données et ML",
    #     "required_skills": ["Python", "SQL", "Machine Learning"],
    #     "experience_required": "2-3 ans",
    #     "education_required": "Master en informatique"
    # }

    calculator = CVJobEmbeddingSimilarity(model_type="sentence_transformer")
    if calculator.model is not None:
        result = calculator.calculate_comprehensive_embedding_similarity(cv_data, job_data)
        print(f"Score global: {result['overall_similarity_score']}% ({result['similarity_level']})")
        print(calculator.generate_detailed_report(cv_data, job_data))
