# Rankify Frontend

Vue 3 + TypeScript single-page app powered by Vite. The UI is intentionally minimal and focuses on quick ranking interactions and crisp comparisons.

## Commands

```bash
npm install        # install deps
npm run dev        # start dev server on :5173
npm run test       # Vitest + Testing Library
npm run lint       # type-check via vue-tsc
npm run format     # Prettier source files
```

The dev server expects a FastAPI backend on `VITE_API_BASE_URL` (defaults to `http://localhost:8000`). Update `.env` in the repo root to change this value for Docker Compose.
