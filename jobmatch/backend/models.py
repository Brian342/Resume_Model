"""
Models.py - Pydantic Schemas for JobMatch API
===============================================================
These define the shape of every request body and response in the API.
FastAPI uses these to:
    -Validate incoming JSON automatically
    -Generate the /docs Swagger UI
    -Serialize outgoing responses
    
PATTERN:
    -*Create -> What the client sends when creating something (no id, no timestamps)
    -*Update -> WHat the client sends when editing (all fields optional)
    -*Out -> What the API returns (Includes id, timestamps, computed fields)
    -*Token -> auth-related payloads
    
Roles (mirrors Your SQLite app):
    -"Seeker" -> Job Seekers who browse and apply
    -"employer"-> Companies that post jobs and review applicants 
"""
