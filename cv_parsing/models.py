from typing import List
from pydantic import BaseModel

class EducationItem(BaseModel):
    degree: str
    institution_name: str
    graduation_year: str

class ExperienceItem(BaseModel):
    job_title: str
    company_name: str
    years_worked: str
    description: str

class CandidateInfo(BaseModel):
    name: str
    email: str
    phone: str
    skills: List[str]
    education: List[EducationItem]
    experience: List[ExperienceItem]
    certifications: List[str]
    languages: List[str]
