"""Émet un JWT de développement pour un utilisateur existant (l'epic Auth fournira /auth/*).

Usage : python -m scripts.issue_token admin@demo.smartcampus.invalid [minutes]
"""

import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models import User

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python -m scripts.issue_token <email> [minutes]")
    settings = get_settings()
    if settings.environment == "production":
        sys.exit("Refusé : outil de développement uniquement.")
    email, minutes = sys.argv[1].lower(), int(sys.argv[2]) if len(sys.argv) > 2 else None
    engine = create_engine(settings.database_url)
    with Session(engine) as db:
        user = db.scalars(select(User).where(User.email == email, User.is_active)).first()
        if user is None:
            sys.exit(f"Utilisateur actif introuvable : {email}")
        print(create_access_token(user.id, [r.code.value for r in user.roles], minutes))
