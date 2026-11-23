# SA-8 — Initialiser le Frontend

- Technologies : Next.js, React, TypeScript, CSS.
- Page : accueil de SmartCampus AI.
- Fonction opérationnelle : vérifier la santé du Backend FastAPI via `GET /api/v1/health`.
- Autres fonctions : interfaces de présentation uniquement, à connecter plus tard.

## Lancer

```powershell
npm install
npm run dev
```

Ouvrir http://localhost:3000.

Le Backend doit être lancé séparément sur http://127.0.0.1:8000 pour voir l'état « API connectée ».

Si son URL change : copier `.env.example` vers `.env.local` et modifier la variable `NEXT_PUBLIC_API_BASE_URL`, puis relancer Next.js.
