# Open Manufacturing Hub Frontend

React + TypeScript + Vite UI for the Open Manufacturing Hub MVP.

## Run locally

```bash
npm install
npm run dev
```

By default the frontend calls `http://localhost:8000`.
Override it with:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Build

```bash
npm run build
```

## UI smoke

```bash
npm run smoke:ui
```

The smoke runner creates a temporary SQLite backend database, starts backend
and frontend on free localhost ports, and checks the main routes, language
switcher, transforms, business rules, resolvers, visual flow builder preview
and mobile viewport. If Chromium is missing, install it once:

```bash
npx playwright install chromium
```

To validate the already running Docker/dev stack in the browser-visible mode:

```bash
npm run smoke:ui:live
```
