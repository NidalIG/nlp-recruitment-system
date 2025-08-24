import json
import numpy as np
from cv_parsing.pipeline import run_cv_parsing
from job_parsing import parse_job
from cv_job_matching import CVJobEmbeddingSimilarity

# --- 1. Traiter le CV ---
cv_file_paths = ["NajibIlham (3).pdf"]
cv_df = run_cv_parsing(cv_file_paths, output_json_path="cv_parsed.json")

# Récupérer le JSON Gemini pour le premier CV
cv_data = json.loads(cv_df['gemini_json_extracted'][0])  # dict compatible

# --- 2. Traiter la Job Description ---
with open("job_text.txt", "r", encoding="utf-8") as f:
    job_text = f.read()
job_data = parse_job(job_text)

# --- 3. Calculer la similarité ---
calculator = CVJobEmbeddingSimilarity(model_type="sentence_transformer")
result = calculator.calculate_comprehensive_embedding_similarity(cv_data, job_data)

# --- 4. Générer le rapport détaillé ---
report = calculator.generate_detailed_report(cv_data, job_data)

def convert_numpy(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_numpy(v) for v in obj]
    return obj

# --- 5. Sauvegarder le résultat ---
with open("cv_job_matching_result.json", "w", encoding="utf-8") as f:
    json.dump(convert_numpy(result), f, ensure_ascii=False, indent=4)


print("=== RAPPORT DE SIMILARITÉ ===")
print(report)
