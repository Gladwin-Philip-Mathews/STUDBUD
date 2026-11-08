# STUDBUD

StudBud: a campus platform that helps RIT Dubai students find study partners and connect safely, with verified RIT accounts, connection requests, reporting and moderation. SWEN 261 team project (Section 600, Fall 2026).

## Team
Advika Pathak, Janani N. Tharkesh, Jason Venkataraghavan, Gladwin Mathews, Ashraf-Ruslan Maktabi

## Stack
Python 3.11, Flask, SQLite, pytest. (Confirm at the first team meeting; see M3-Q-01.)

## Run it
```
python -m venv .venv
.venv\Scripts\activate        # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env        # Mac/Linux: cp .env.example .env
flask --app app run --debug
pytest
```

## Project layout
```
app/controllers/     web layer, one per feature group
app/services/        business rules (AuthService, ConnectionService, ...)
app/repositories/    persistence behind interfaces
app/models/          Account, Profile, Connection, ...
app/email_gateway/   EmailGateway (stub and live)
tests/
docs/                SRS, M3 design, diagrams
```

## Working rules
See [CONTRIBUTING.md](CONTRIBUTING.md). Short version: never push to `main`; use a branch and a pull request with one review.
