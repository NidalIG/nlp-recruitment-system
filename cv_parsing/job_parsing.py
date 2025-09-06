import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'API Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def parse_job(job_text: str) -> dict:
    """
    Parse un texte d'offre d'emploi en utilisant l'API Gemini pour extraire les informations structurées.
    
    Args:
        job_text (str): Le texte brut de l'offre d'emploi
        
    Returns:
        dict: Un dictionnaire contenant les informations extraites de l'offre
    """
    
    prompt = f"""
    Analyse le texte d'offre d'emploi suivant et extrait les informations demandées au format JSON exact.
    
    Texte de l'offre d'emploi :
    {job_text}
    
    Extrait les informations suivantes et retourne UNIQUEMENT un JSON valide avec cette structure exacte :
    {{
        "title": "titre du poste (ou null si non trouvé)",
        "company": "nom de l'entreprise (ou null si non trouvé)",
        "location": "localisation (ou null si non trouvé)",
        "contract": "type de contrat : CDI, CDD, INTERNSHIP, STAGE, FREELANCE (ou null si non trouvé)",
        "required_skills": ["liste", "des", "compétences", "techniques", "requises"],
        "experience_required": "années d'expérience requises (ou null si non trouvé)",
        "education_required": "niveau d'éducation requis (ou null si non trouvé)",
        "responsibilities": ["liste", "des", "responsabilités", "principales"]
    }}
    
    Règles importantes :
    - Retourne UNIQUEMENT le JSON, pas de texte supplémentaire
    - Utilise null pour les valeurs non trouvées (pas de chaînes vides)
    - Pour les compétences, inclus les technologies, langages de programmation, outils, etc.
    - Pour les responsabilités, liste les tâches principales du poste
    - Normalise le type de contrat en majuscules
    """
    
    try:
        # Initialiser le modèle Gemini
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Générer la réponse
        response = model.generate_content(prompt)
        
        # Nettoyer la réponse pour enlever ```json ou ```
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[len("```json"):].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:].strip()
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()
        
        # Parser la réponse JSON
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"Erreur de parsing JSON : {e}")
            print(f"Réponse brute : {raw_text}")
            result = {}
        
        # Validation et nettoyage des données
        cleaned_result = {
            "title": result.get("title"),
            "company": result.get("company"),
            "location": result.get("location"),
            "contract": result.get("contract"),
            "required_skills": result.get("required_skills", []) if isinstance(result.get("required_skills"), list) else [],
            "experience_required": result.get("experience_required"),
            "education_required": result.get("education_required"),
            "responsibilities": result.get("responsibilities", []) if isinstance(result.get("responsibilities"), list) else []
        }
        
        return cleaned_result
        
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API Gemini : {e}")
        return {
            "title": None,
            "company": None,
            "location": None,
            "contract": None,
            "required_skills": [],
            "experience_required": None,
            "education_required": None,
            "responsibilities": []
        }


# Exemple d'utilisation