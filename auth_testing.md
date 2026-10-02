# Existing JWT authentication — verification checklist

## Scope
UI refresh only. No authentication implementation, password, token configuration, or API contract changes.
The authentication integration reference was consulted before restoring the existing startup seed after the preview PostgreSQL cluster was reinitialized on 2026-10-02.

## Existing architecture
- FastAPI + PostgreSQL + SQLAlchemy (not MongoDB).
- Existing password hashing, JWT implementation, and idempotent `seed_if_empty` are unchanged.
- Credentials: `/app/memory/test_credentials.md`.
- Read the external preview base URL from `/app/frontend/.env`.

## Verification (adapted to existing API, do not migrate authentication)
1. Verify database role and database exist; do not reset populated data or rotate secrets.
2. Verify seed creates users only in the fresh empty database and a subsequent startup does not duplicate them.
3. POST `/api/auth/login` with the documented admin credentials. Expect successful existing token/user response.
4. GET `/api/auth/me` using the existing Bearer token contract. Expect matching user.
5. Check browser sign-in, authenticated navigation, and sign-out without console errors.
6. Check a restricted seeded role's sidebar permissions are unchanged.
7. Update test credentials documentation whenever accounts are created or credentials change.

## Preview recovery note
The missing database role/database were recreated from the existing DATABASE_URL. The existing application startup recreates demo data. Previous preview-only custom records were not recovered; no backup was present in the workspace.