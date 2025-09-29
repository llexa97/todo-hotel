# Repository Guidelines

## Project Structure & Module Organization
The Flask application lives in `app/`: `routes_main.py` serves the web UI, `routes_api.py` exposes JSON endpoints, `models.py` defines the SQLAlchemy layer, and `utils.py` hosts shared helpers. Templates sit in `app/templates`, static assets in `app/static`. Local data defaults to `instance/todo_hotel.db`, with migrations tracked under `migrations/`. Support scripts (`generate_weekly_tasks.py`, `clear_all_tasks.py`) remain at the repository root; `wsgi.py` plus `logs/`, `data/`, and `backups/` handle deployment and exports.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate` — initialise a dedicated virtual environment.
- `pip install -r requirements.txt` — install Flask, Alembic, pytest, and other pinned dependencies.
- `flask --app app:create_app run --debug --port 8081` — launch the development server with both blueprints enabled.
- `flask --app app:create_app db upgrade` — apply outstanding Alembic migrations to the active database.
- `pytest` — run the automated suite (add `-q` for terse output or `-k <pattern>` to filter cases).
- `gunicorn -b 0.0.0.0:8081 wsgi:app` — start the production entrypoint for container or service deployments.

## Coding Style & Naming Conventions
Use PEP 8 with four-space indentation and snake_case for functions, helpers, and modules. Reserve PascalCase for SQLAlchemy models and future form classes. Keep route functions aligned with their HTTP verbs (`create_task`, `toggle_task_status`) and reuse the structured logging format introduced in `app/__init__.py`.

## Testing Guidelines
pytest is available but no suites ship yet; place new tests under a `tests/` package, naming files `test_*.py`. Build fixtures around an in-memory SQLite database (`SQLALCHEMY_DATABASE_URI="sqlite://"`) so CRUD logic in `Task` and the blueprints remains isolated. Cover edge cases for weekend calculations, duplicate prevention in `create_task_if_not_exists`, and API status codes. Keep external scripts mocked to avoid mutating real data or logs.

## Commit & Pull Request Guidelines
Write imperative English commit subjects (`Add weekend filter`, `Fix task ordering`) and group related changes with their migrations. Pull requests should summarise intent, list verification steps (`pytest`, `flask db upgrade`), attach screenshots for UI tweaks, and cross-reference issue IDs or incident notes when relevant. Mention any manual scripts executed during validation.

## Security & Configuration Tips
Store environment variables in `.env` (`FLASK_ENV`, `DATABASE_URL`, `SECRET_KEY`) and keep production secrets out of version control. Ensure `logs/` and `backups/` remain writable by the service user but excluded from commits. In production, run `gunicorn` behind a supervisor and monitor the rotating log files configured in `setup_logging`.
