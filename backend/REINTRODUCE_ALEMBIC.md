# Reintroducing Alembic (Post-MVP)

During MVP we use **schema bootstrap** via `Base.metadata.create_all()` on API startup. No migrations. When the schema stabilizes, reintroduce Alembic as follows.

## Minimal plan

1. **Add dependency**
   - In `backend/requirements.txt`: add `alembic==1.12.1` (or current).

2. **Init Alembic**
   ```bash
   cd backend && alembic init alembic
   ```

3. **Configure `alembic/env.py`**
   - Set `target_metadata = Base.metadata` (import `Base` from `app.db.session`).
   - Ensure **all models are imported** before `target_metadata` is used (e.g. `import app.db.models`).
   - Use `config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", "..."))` or your existing config.

4. **Generate initial migration**
   ```bash
   alembic revision --autogenerate -m "initial"
   ```
   - Review the generated migration. It should create all tables from current models.
   - **Existing DBs:** Either reset (`make reset-db`) or apply the migration manually. Existing data may require a custom migration (e.g. create tables only if not present, or backfill).

5. **Replace bootstrap with migrations**
   - Remove the `init_db(engine)` call from FastAPI lifespan (or restrict it to dev-only).
   - On startup, run `alembic upgrade head` (e.g. in Dockerfile `command` or a startup script) **before** starting uvicorn.
   - Ensure `create_all` is no longer used for schema creation in production.

6. **Docker / Makefile**
   - Update `docker-compose` API `command` to run `alembic upgrade head` then uvicorn.
   - Add `make migrate` back if desired: `docker compose exec api alembic upgrade head`.

7. **Documentation**
   - Update README: schema is now managed by Alembic; mention `make migrate` and `make reset-db` where relevant.

## Notes

- **Existing DBs:** Resetting (`make reset-db`) is simplest. If you must keep data, the initial migration may need to create tables only when missing, or you may need a one-off data migration.
- **Bootstrap code:** Keep `app/db/bootstrap.py` and `init_db` only if you still use them (e.g. tests or dev); otherwise remove or gut them once fully on Alembic.
