import re
import json

# Fonctions d'extraction simplifiées
def extract_title(text):
    match = re.search(r"(?i)(Data Scientist|Engineer|Developer|Manager|Analyst)", text)
    return match.group(0) if match else None

def extract_company(text):
    match = re.search(r"at ([A-Z][A-Za-z0-9& ]+)", text)
    return match.group(1).strip() if match else None

def extract_location(text):
    match = re.search(r"in ([A-Z][a-zA-Z ]+)", text)
    return match.group(1).strip() if match else None

def extract_contract(text):
    match = re.search(r"(CDI|CDD|Internship|Stage|Freelance)", text, re.IGNORECASE)
    return match.group(1).upper() if match else None

def extract_skills(text):
    skill_list = ["Python", "SQL", "Machine Learning", "Deep Learning", "NLP", "Java", "C++", "React", "Spring Boot"]
    return [skill for skill in skill_list if re.search(skill, text, re.IGNORECASE)]

def extract_experience(text):
    match = re.search(r"(\d+\s+years?|\d+ ans)", text)
    return match.group(1) if match else None

def extract_education(text):
    match = re.search(r"(Bachelor|Master|PhD|Bac\+\d)", text, re.IGNORECASE)
    return match.group(1) if match else None

def extract_responsibilities(text):
    lines = text.split("\n")
    responsibilities = []
    capture = False
    for line in lines:
        if "Responsibilities" in line:
            capture = True
            continue
        if capture:
            if line.strip() == "" or re.search(r"Requirements", line):
                break
            responsibilities.append(line.strip("- "))
    return responsibilities

def parse_job(job_text: str) -> dict:
    return {
        "title": extract_title(job_text),
        "company": extract_company(job_text),
        "location": extract_location(job_text),
        "contract": extract_contract(job_text),
        "required_skills": extract_skills(job_text),
        "experience_required": extract_experience(job_text),
        "education_required": extract_education(job_text),
        "responsibilities": extract_responsibilities(job_text)
    }

