# Web

Next.js, React, and TypeScript starter using the App Router and CSS modules.
Install Node.js 24.3 or newer and follow the [repository setup](../README.md).

## Run

On first setup, copy `web/.env.example` to `web/.env.local`:

```powershell
Copy-Item web/.env.example web/.env.local
```

Keep an existing `.env.local` and add any missing settings instead of overwriting
it. Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` to
the URL and publishable key for the same Supabase project used by the backend.
Set `NEXT_PUBLIC_API_URL` to your backend address; the default is
`http://localhost:18000`.

The repository root `.env` configures the backend; the web application reads
its own `web/.env.local`. All `NEXT_PUBLIC_` values are included in browser code.
Never use a Supabase service-role key, secret key, or database password in web
configuration. Restart the development server after changing these settings;
production builds must be rebuilt with the correct public values.

From the repository root:

```bash
cd web
npm ci
npm run dev
```

Open http://localhost:3000. Stop with Ctrl+C; edits reload automatically.
Docker runs the backend and database separately.

## Login and account setup

Login checks credentials with Supabase Auth, then loads the user's profile from
the backend's `GET /auth/me` endpoint. The backend must be running and the account
must have an active row in `public.users` with the same ID as its Supabase Auth
user. A Supabase Auth account alone does not grant access to the portal.

Accounts are provisioned by an authenticated administrator through the backend's
`POST /auth/signup` endpoint. Self-service sign-up is disabled in the web UI.
The previous demo credentials are no longer supported; use an account that an
administrator has provisioned.

After login, the page displays the account's name and role and offers sign-out.
Attendance dashboards and face enrollment are not connected to this page yet.
The dormant sign-up camera preview stays in browser memory and is not uploaded,
saved, or matched.

## Checks

From `web/`:

```bash
npm run lint
npx --no-install next typegen
npx --no-install tsc --noEmit
npm run build
```

`src/app/` contains the page, layout, and styles; `public/` holds static assets.
`src/lib/supabase.ts` creates the browser authentication client. Missing public
Supabase settings leave login unavailable and display a configuration error.
