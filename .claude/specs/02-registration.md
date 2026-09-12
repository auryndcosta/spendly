# Spec: Registration

## Overview
This step implements account creation for Spendly. `GET /register` already
renders `register.html`, but submitting the form does nothing yet. This step
adds the `POST /register` handler that validates input, hashes the password,
inserts a new row into `users`, and gets the visitor to a working account so
later steps (login, profile, expenses) have a real user to attach data to.

## Depends on
- Step 1 (Database setup) — requires the `users` table and `get_db()` to exist.

## Routes
- `POST /register` — validate registration form input, create the user, redirect to `login` (with `registered=1`) on success — public
- `GET /register` — unchanged, still renders `register.html` — public
- `GET /login` — unchanged behavior, but now also reads the optional `registered` query arg and passes a `success` message into the template — public. This is a display-only addition; POST /login (authentication) is not part of this step.

## Database changes
No schema changes. `users` table already supports everything needed
(`name`, `email` unique, `password_hash`, `created_at`).

New functions in `database/db.py` (logic, not schema):
- `get_user_by_email(email)` — returns a row or `None`, used to check for duplicates
- `create_user(name, email, password)` — hashes the password with werkzeug and inserts the row, returns the new user id

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — change `<form method="POST" action="/register">` to use `action="{{ url_for('register') }}"` instead of a hardcoded path; keep the existing `{% if error %}` block, which the new route will populate on validation failures; add a `confirm_password` field (mirroring the `password` field) so the user re-enters their password
  - `templates/login.html` — add a `{% if success %}<div class="auth-success">{{ success }}</div>{% endif %}` block (mirroring the existing `auth-error` block) to show the post-registration confirmation

## Files to change
- `app.py` — add `methods=["GET", "POST"]` to the `register` route, handle form validation and the redirect on success (`redirect(url_for('login', registered=1))`); update the `login` route to set `success` in the render context when `request.args.get("registered")` is present
- `database/db.py` — add `get_user_by_email()` and `create_user()`
- `templates/register.html` — fix hardcoded form action
- `templates/login.html` — add success banner block
- `static/css/style.css` — add an `.auth-success` rule next to `.auth-error`, using existing CSS variables (e.g. `var(--accent)`, `var(--accent-light)`, `var(--border)`) — no hardcoded hex values

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline SQL in `app.py` — all queries live in `database/db.py`
- Validate on the server even though the form has `required`/`type=email` attributes (never trust client-side validation alone)
- Minimum password length: 8 characters, matching the existing placeholder text in `register.html`
- `password` and `confirm_password` must match — validated server-side, checked after the length check and before the duplicate-email check
- On duplicate email, re-render `register.html` with `error` set — do not raise an unhandled exception
- All redirects use `redirect(url_for(...))` — never a hardcoded path string
- Do not implement `/login` POST handling (authentication), `/logout`, or `/profile` — those are later steps. The `login` route change in this spec is limited to displaying an optional success message; it does not add session/auth logic
- New CSS uses variables only, matching `:root` in `style.css` — no hardcoded hex values

## Definition of done
- [ ] `GET /register` still renders the form with no errors
- [ ] Submitting valid name/email/password creates a new row in `users` with a hashed password (verify via sqlite3 CLI or a quick script)
- [ ] Submitting an email that already exists re-renders `register.html` with an error message and does not insert a duplicate row
- [ ] Submitting a password under 8 characters re-renders `register.html` with an error message and does not insert a row
- [ ] Submitting a password and confirm-password that don't match re-renders `register.html` with an error message and does not insert a row
- [ ] After a successful registration, the browser is redirected to `/login?registered=1` and the login page shows a success banner
- [ ] Visiting `/login` directly (no query arg) shows no banner
- [ ] `app.py` contains no raw SQL — only calls into `database/db.py`
- [ ] `pytest` passes with no regressions to existing routes
