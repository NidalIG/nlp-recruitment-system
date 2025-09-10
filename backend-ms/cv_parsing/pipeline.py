import pandas as pd
import ast
from tqdm import tqdm
from cv_parsing.extractors import extract_text
from cv_parsing.gemini_parser import parse_cv_with_gemini

def run_cv_parsing(file_paths: list, output_json_path: str):
    # Extraction texte
    extracted_list = [extract_text(file) for file in tqdm(file_paths)]

    # Parsing via Gemini
    all_results = [parse_cv_with_gemini(text) for text in tqdm(extracted_list)]

    # Sauvegarde JSON
    result_df = pd.DataFrame({
        "file_path": file_paths,
        "fulltext_extracted": extracted_list,
        "gemini_json_extracted": all_results,
    })
    result_df.to_json(output_json_path, orient="records", indent=4)

    return result_df