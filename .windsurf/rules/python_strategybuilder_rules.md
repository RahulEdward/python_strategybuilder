---
trigger: always_on
---

CT Windsurf Rules – Expert Guidelines for Strategy Builder SaaS App
1. Project Structure Rule
Use a modular vertical structure with the following layout:

pgsql
Copy
Edit
project/
├── app/
│   ├── api/routes/          → Feature-based route files (auth, builder, dashboard)
│   ├── models/              → SQLAlchemy models (User, Strategy)
│   ├── schemas/             → Pydantic request/response models
│   ├── crud/                → Reusable DB logic (get/create/update)
│   ├── services/            → Business logic (auth_service, code_generator)
│   ├── templates/           → HTML pages using Jinja2 (dev phase only)
│   ├── static/              → CSS/JS files (Tailwind, scripts)
│   ├── db/                  → DB engine and session config
│   ├── core/                → Settings, security, config loaders
│   └── main.py              → FastAPI app entry point
├── datasets/                → Uploaded files (future)
├── .env                     → Secret keys, DB configs
├── .gitignore               → Ignore .env, venv/, __pycache__, etc.
├── requirements.txt         → Python dependencies
├── README.md                → Project usage and dev guide
├── LICENSE                  → MIT by default
2. Routing Rule
All routes must use FastAPI APIRouter

Each major feature (auth, builder, dashboard) must have its own route file

Use RESTful route naming: /login, /builder, /strategies

3. Authentication Rule
Use bcrypt for password hashing

Implement JWT tokens for secure authentication

Store token in secure HTTP-only cookies

Protect routes using Depends(get_current_user)

Include login, register, logout routes with complete session/token handling

4. Database Rule
Use SQLAlchemy ORM with SQLite (for dev) and PostgreSQL (for prod)

Create models for:

User: id, username, email, password_hash

Strategy: id, user_id, name, rules (JSON), generated_code, created_at

Use a base model from db/base.py

All DB sessions must use db/session.py

5. Code Generator Rule
Create a services/code_generator.py file

Convert form inputs (indicators, operators, values) into valid Python code

Code must be readable, executable, and modular

Support expansion to PineScript later

6. Form Builder Rule
Form should support:

Multiple condition rows

Indicator selection

Operators (>, <, ==, crossover)

Input for value or second indicator

SL/TP/Capital fields

Use TailwindCSS for form layout

POST the form to /builder to generate code

7. UI and Styling Rule
Use TailwindCSS via CDN only

Optional: DaisyUI for dark/light toggle

All CSS in static/css/, all JS in static/js/

No inline styles or scripts allowed

All templates must extend base.html

8. Templates Rule
Jinja2 is used only during early development

All templates must follow:

{% extends "base.html" %}

Include header, footer, navigation, and dark mode toggle

Pages include: home.html, login.html, register.html, builder.html, dashboard.html

9. Strategy Management Rule
Save strategy per user

Show strategy list in dashboard

Allow viewing generated code

Do not allow unauthenticated access to strategies

10. Security Rule
Never store plain passwords

Protect all user routes with JWT validation

Logout must delete token from cookie

Secure .env with secret keys and database URL

11. Deployment Rule
Run app on port 5001 by default

Use uvicorn app.main:app --reload --port 5001

Include Dockerfile, docker-compose.yaml in future

12. Documentation Rule
README.md must include:

Project summary

Tech stack

Setup instructions

How to use builder

How to contribute

Use MIT license in LICENSE file

13. Static File Rule
Do not use inline JS or CSS

Tailwind must be loaded from CDN in base.html

JS files for dynamic form behavior must be inside static/js/

14. Code Style Rule
Follow PEP8 at all times

Use black for auto-formatting

Use isort for import sorting

Write meaningful function and variable names

Use reusable components/functions only

15. Future Expansion Rule
Your structure must support plug-and-play expansion of:

multi-language code generation

Strategy backtesting engine

CSV/Live data uploading

AI assistant (prompt → code)

Subscription system with billing

Admin dashboard

Frontend replacement with Next.js

