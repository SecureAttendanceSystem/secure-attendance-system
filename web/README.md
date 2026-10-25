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

## Login and sign-up preview

The frontend currently contains only the login and sign-up screens. Use either
sample account to test the login form:

- Student: `student@unb.ca` / `Student123!`
- Professor: `professor@unb.ca` / `Professor123!`

Sign-up lets you choose a student or professor account and requires a temporary
camera preview. The preview stays in browser memory and is not uploaded, saved,
or matched. Demo accounts are kept in page memory and reset when the page is
refreshed. Authentication and face verification still need a backend before
accounts can be used beyond this prototype.

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
