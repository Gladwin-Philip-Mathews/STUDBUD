# STUDBUD

StudBud: a campus platform that helps RIT Dubai students find study partners and connect safely, with verified RIT accounts, connection requests, reporting and moderation. SWEN 261 team project (Section 600, Fall 2026).

## Team
Advika Pathak, Janani N. Tharkesh, Jason Venkataraghavan, Gladwin Mathews, Ashraf-Ruslan Maktabi

## Stack
Angular 20 (frontend), Python 3.11 with Flask (backend JSON API), SQLite, pytest. Node 20.19 or newer is required for Angular. (Confirm at the first team meeting; see M3-Q-01.)

## Run it
Backend (terminal 1):
```
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env        # Mac/Linux: cp .env.example .env
flask --app app run --debug --port 5000
pytest
python seed_demo.py           # optional: demo courses, communities, an admin, a moderator and students (password Demo1234)
```

Frontend (terminal 2):
```
cd frontend
npm install
npm start                     # http://localhost:4200 (calls /api through a proxy to port 5000)
npm test
```

## Project layout
```
backend/
  app/controllers/     JSON API endpoints, one file per feature (blueprints register automatically)
  app/schema/          one .sql file per feature
  app/services/        business rules (AuthService, ConnectionService, ...)
  app/repositories/    persistence behind interfaces
  app/models/          Account, Profile, Connection, ...
  app/email_gateway/   EmailGateway (stub and live)
  tests/
frontend/              Angular app (screens call the /api endpoints)
docs/                  SRS, M3 design, diagrams
```

## Adding your feature
See [docs/feature-guide.md](docs/feature-guide.md) for who owns what and a step-by-step recipe.

## Working rules
See [CONTRIBUTING.md](CONTRIBUTING.md). Short version: never push to `main`; use a branch and a pull request with one review.
