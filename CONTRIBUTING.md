# Working agreement

## Branches
- `main` is always working. **Never commit or push directly to `main`.**
- Branch from an up-to-date `main`: `type/ID-short-description`
  - types: `feature`, `fix`, `chore`, `docs`, `test`
  - examples: `feature/FR-042-refusal-rules`, `fix/FR-084-resend-count`

## Commits
- Small and focused. Format: `FR-042: apply refusal rules in order`
- Include the requirement or design ID (FR, NFR, DR, DD, CH) whenever there is one.

## Pull requests
1. Push your branch and open a pull request into `main`.
2. Fill in the template (requirements covered, how tested).
3. CI must pass and **one teammate must review and approve**.
4. The author merges with *Squash and merge*, then deletes the branch.
5. Do not review your own pull request.

## Code
- Layers follow the M3 design: controllers -> services -> repositories. Rules live in services; persistence only in repositories (DD-10).
- Limits (resend count, lock-out, session time...) are settings, not constants in code (DD-08).
- Email only goes through `EmailGateway` (DD-03).
- Every service has unit tests written from the acceptance criteria.

## Secrets
Never commit `.env`, passwords, keys, or database files.
