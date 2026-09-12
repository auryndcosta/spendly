# Spec: Login and Logout

## Overview
Spendly currently lets users register (Step 2) but has no way to actually authenticate. `GET /login` only renders the sign-in form and `GET /logout` is a stub string. This step wires up real session-based authentication: submitting the login form verifies credentials against the `users` table and starts a session, and logging out clears that session. This is the foundation every later logged-in-only page (`/profile`, `/expenses/*`) will depend on.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user()`, `get_user_by_email()`, existing accounts to log in with)

## Routes
- `POST /login` — verify email/password against `users`, start session, redirect to landing page (or a `next` target) — public
- `GET /login` — existing, unchanged behavior (renders form, shows `registered`/error messages) — public
- `GET /logout` — clear the session, redirect to `login` — logged-in (safe no-op if no session exists)

## Database changes
No database changes. `users.password_hash` already exists from Step 01 and is sufficient for `check_password_hash` comparisons.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — change `<form action="/login">` to `<form action="{{ url_for('login') }}">` (hardcoded URL, violates project rules) and render a login-failure error using the existing `.auth-error` block
  - `templates/base.html` — nav should show "Log out" instead of "Sign in" / "Get started" when a session user is active

## Files to change
- `app.py` — add `app.secret_key`, extend `login` route to accept `POST`, implement `logout` route, import `check_password_hash`
- `templates/login.html` — fix hardcoded form action, surface login errors
- `templates/base.html` — conditional nav based on session state

## Files to create
No new files.

## New dependencies
No new dependencies. Uses Flask's built-in `session` and `werkzeug.security.check_password_hash`, both already available.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`check_password_hash` against the stored `password_hash`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use Flask's `session` for auth state (`session["user_id"]`) — no new "sessions" DB table
- `app.secret_key` must be set for sessions to work — read from an environment variable with a dev fallback, never a hardcoded production secret
- Do not touch `/profile` or `/expenses/*` stub routes — those belong to Steps 4, 7, 8, 9
- Reuse `get_user_by_email()` from `database/db.py`; do not put query logic inline in `app.py`
- Never hardcode URLs in templates — always use `url_for()`

## Definition of done
- [ ] Submitting the login form with the seeded demo account (`demo@spendly.com` / `demo123`) redirects away from `/login` and sets a session cookie
- [ ] Submitting the login form with a wrong password re-renders `login.html` with an error and does not set a session
- [ ] Submitting the login form with an email that doesn't exist re-renders `login.html` with an error (no user enumeration difference in message wording)
- [ ] Visiting `/logout` after logging in clears the session and redirects to `/login`
- [ ] Visiting `/logout` without an active session does not error — redirects to `/login` cleanly
- [ ] After logging in, the navbar shows "Log out" instead of "Sign in" / "Get started"
- [ ] After logging out, the navbar reverts to showing "Sign in" / "Get started"
- [ ] No hardcoded URLs remain in `login.html`
