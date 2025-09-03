# models/user.py
from datetime import datetime

def create_user(email, password_hash, first_name=None, last_name=None, role="user", profile=None):
    return {
        "email": email.lower(),
        "password": password_hash,  # hash déjà généré par bcrypt
        "firstName": first_name,
        "lastName": last_name,
        "role": role,
        "profile": profile or {},
        "refreshTokens": [],
        "createdAt": datetime.utcnow().isoformat()
    }
