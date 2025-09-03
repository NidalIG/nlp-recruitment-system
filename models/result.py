# models/result.py
from datetime import datetime
from bson import ObjectId

def create_result(user_id, type, data, meta=None, refs=None):
    return {
        "user": ObjectId(user_id),
        "type": type,  # "cv", "job", "matching", "quiz"
        "data": data,
        "meta": meta or {},
        "refs": refs or {},
        "createdAt": datetime.utcnow()
    }
