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

Copy `frontend/.env.example` to `frontend/.env` to configure `VITE_API_BASE_URL`. Inside Docker Compose the frontend talks to `http://backend:8000`; for local development outside containers, adjust the URL to `http://localhost:8000` instead.
