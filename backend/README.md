# SA-7 - Initialiser le Backend de SmartCampus AI

## Objectif
Créer la base du backend avec **Python + FastAPI** : application, structure de dossiers, API versionnée, documentation et tests.

## Étapes (Windows PowerShell)

```powershell
cd SA7_Backend_SmartCampus
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Si l'activation est bloquée, utiliser directement `.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`, puis `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.

## Vérifier

- Swagger (documentation) : http://127.0.0.1:8000/docs
- Santé de l'API : http://127.0.0.1:8000/api/v1/health
- Réponse attendue : `{"status":"ok","service":"smartcampus-backend"}`

Dans un autre terminal, à la racine du projet :

```powershell
pytest -q
```

## Structure

```text
app/
  main.py                   # Crée l'application FastAPI
  api/v1/router.py          # Regroupe les routes v1
  api/v1/endpoints/health.py# Vérification de l'API
tests/test_app.py           # 3 tests HTTP
requirements.txt           # Dépendances principales
requirements-dev.txt       # Dépendances de test
.env.example               # Exemple de configuration locale
```

## Limites et prochaines étapes

Ceci est uniquement **l'initialisation du backend**. L'authentification, PostgreSQL, le chatbot/agent IA, le RAG, le LLM SQL, les notifications et les API métier (SA-5) ne sont **pas encore implémentés**. Les connexions et droits d'accès seront ajoutés ensuite. Ne pas utiliser ce prototype comme service de production.
