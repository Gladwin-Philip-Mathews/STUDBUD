# Feature guide: who owns what and how to add your feature

## Ownership
| Owner | Feature | M3 process | Requirements | Your folders |
|---|---|---|---|---|
| Gladwin | Accounts (done), connections, notifications, pilot measures | 1.0, 4.0, 7.0, 8.0 | FR-001-009, FR-040-048, FR-080-084, FR-090-092 | `auth`, `connections`, `notifications` |
| Advika | Profiles, interests, courses, suggestions | 2.0 | FR-010-015 | `profiles` |
| Jason | Communities, posts, replies | 3.0 | FR-020-025, FR-030-038 | `communities` |
| Ashraf-Ruslan | Messaging, admin pages | 5.0, 9.0 | FR-050-054, FR-100-104 | `messaging`, `admin` |
| Janani | Safety reports, moderation | 6.0 | FR-060-070 | `moderation` |

Build Must requirements first, then Should. Take the rules from the M3 design and the acceptance criteria (AC-FR-xxx) from the SRS.

## Recipe: add your feature (replace `profiles` with yours)
Everything below is a NEW file in your own name. You should not need to edit shared files.

**Backend (`backend/`)**
1. Tables: add `CREATE TABLE IF NOT EXISTS ...` to your file in `app/schema/` (for example `10_profiles.sql`).
2. Entities and enums: add a file in `app/models/` (do not edit `entities.py`).
3. Repository: interface and SQLite class in `app/repositories/<feature>_repo.py`.
4. Service: `app/services/<feature>_service.py`. Register it:
   ```python
   from ..container import service

   @service("profiles")
   def build(d):                 # d has db, settings, accounts, profiles, connections, notifications, gateway, clock, config
       return ProfileService(d.profiles, d.settings)
   ```
5. Controller: `app/controllers/<feature>.py` defining `bp = Blueprint(...)`. It is registered automatically.
   ```python
   from flask import Blueprint, g, jsonify
   from ..container import get_service
   from ..security import login_required, role_required

   bp = Blueprint("profiles", __name__, url_prefix="/api/profile")

   @bp.get("")
   @login_required               # g.account is the signed-in account
   def mine():
       return jsonify(get_service("profiles").get(g.account.id))
   ```
6. Tests: `tests/test_<feature>.py`. Use the `client`, `app`, `clock` and `gateway` fixtures (see `tests/test_auth_api.py` for sign-in helpers).

**Frontend (`frontend/src/app/<feature>/`)**
1. Replace `<feature>-home.ts` with your pages, and add routes in `<feature>.routes.ts`.
2. Call the backend with `HttpClient` under `/api/...`. Do not put business rules in Angular.
3. Add `*.spec.ts` tests next to your code.

## Rules reminder
- Never push to `main`. Branch, pull request, one review, squash and merge (see CONTRIBUTING.md).
- Limits are settings (`app/settings.py`), not constants.
- Email only through `EmailGateway`.
- Run `pytest` in `backend/` and `npm test` in `frontend/` before opening a pull request.
