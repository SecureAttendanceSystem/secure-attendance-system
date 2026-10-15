# Web

Next.js, React, and TypeScript starter using the App Router and CSS modules.
Install Node.js 24.3 or newer and follow the [repository setup](../README.md).

## Run

From the repository root:

```bash
cd web
npm ci
npm run dev
```

Open http://localhost:3000. Stop with Ctrl+C; edits reload automatically.
Docker runs the backend and database separately.

## Checks

From `web/`:

```bash
npm run lint
npx --no-install next typegen
npx --no-install tsc --noEmit
npm run build
```

`src/app/` contains the page, layout, and styles; `public/` holds static assets.
No API client or custom environment variables are implemented yet. Future web
settings belong in `web/.env.local`; `NEXT_PUBLIC_` values are visible in the
browser and must not contain secrets.
