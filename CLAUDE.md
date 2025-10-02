# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Todo Hôtel is a Flask-based task management application designed for hotel weekend operations. It provides both a web UI and REST API for managing recurring and one-time tasks across Friday-Saturday-Sunday weekends.

## Architecture

### Application Structure

The Flask application follows a blueprint-based architecture:

- **`app/__init__.py`**: Application factory (`create_app()`) with SQLAlchemy, Flask-Migrate, and rotating file logging
- **`app/models.py`**: SQLAlchemy `Task` model with fields: `title`, `due_date`, `is_done`, `done_at`, `created_at`, `is_recurring`, `display_order`
- **`app/routes_main.py`**: Web UI blueprint serving HTML templates with three views (weekend/all/completed)
- **`app/routes_api.py`**: JSON API blueprint (`/api/tasks`) with GET/POST endpoints
- **`app/utils.py`**: Business logic including weekend calculation, task deduplication, and script synchronization

### Key Design Patterns

**Weekend Logic**: The application uses `get_target_weekend()` (app/utils.py:179) which calculates the target weekend based on business rules:
- Friday/Saturday/Sunday → current weekend
- Monday-Thursday → next weekend

**Task Deduplication**: `create_task_if_not_exists()` (app/utils.py:47) ensures no duplicate open tasks with the same title+due_date. Returns `(task, 201)` for new tasks or `(existing_task, 409)` for duplicates.

**Script Synchronization**: When creating recurring tasks via API/web, `sync_recurring_task_to_script()` (app/utils.py:222) automatically appends them to `generate_weekly_tasks.py`'s `WEEKLY_TASKS` list with proper `day_offset` (0=Friday, 1=Saturday, 2=Sunday) and incremented `order`.

**Logging**: Structured emoji-prefixed logging throughout (🔨 for creation, ✅ for success, ❌ for errors, etc.) configured in `setup_logging()` with rotating file handlers.

### Database

SQLite database with Alembic migrations. The `Task` model enforces duplicate prevention at the application level (SQLite doesn't support conditional unique constraints). Indexes on `(is_done, created_at)` and `due_date` for query performance.

### Scripts

- **`generate_weekly_tasks.py`**: Standalone script that generates predefined recurring tasks via the API. Runs weekly via cron (Fridays at 06:00). Contains `WEEKLY_TASKS` list defining Friday/Saturday/Sunday tasks with `day_offset` and `order`. Supports `--dry-run`, `--api-url`, `--json` flags.
- **`clear_all_tasks.py`**: Utility to clear all tasks from the database
- **`wsgi.py`**: Production entry point for gunicorn

## Development Commands

### Environment Setup
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### Database Operations
```bash
# Apply migrations
flask --app app:create_app db upgrade

# Create new migration
flask --app app:create_app db migrate -m "description"

# Rollback migration
flask --app app:create_app db downgrade
```

### Running the Application
```bash
# Development server (port 8081)
flask --app app:create_app run --debug --port 8081

# Production with gunicorn
gunicorn -b 0.0.0.0:8081 -w 3 wsgi:app
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_utils.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_weekend"
```

### Recurring Tasks Script
```bash
# Dry run (simulation without creating tasks)
python generate_weekly_tasks.py --dry-run

# Production run with custom API URL
python generate_weekly_tasks.py --api-url http://localhost:8081/api

# JSON output for automation
python generate_weekly_tasks.py --json
```

## Coding Conventions

- **Style**: PEP 8, 4-space indentation, snake_case for functions/variables
- **Models**: PascalCase for SQLAlchemy models (e.g., `Task`)
- **Route Functions**: Named after HTTP verbs and resources (`create_task`, `toggle_task_status`)
- **Logging**: Use emoji-prefixed structured format from `app/__init__.py`:
  - 📝 API calls
  - 🔨 Task creation
  - ✅ Success
  - ❌ Errors
  - 🔍 Debug/queries
  - 📊 Data/statistics

## Important Implementation Details

### Database URL Configuration

The default database URL has a **typo** in production mode (`app/__init__.py:80`):
```python
default_db_url = 'sqlite:////root/todo-hotel/instace/todo_hotel.db'  # Note: "instace" typo
```
This is intentional for backward compatibility. Override with `DATABASE_URL` environment variable for production.

### Environment Variables

Configure via `.env` file:
```bash
FLASK_ENV=production                              # or development
DATABASE_URL=sqlite:////root/todo-hotel/data/todo_hotel.db
SECRET_KEY=<generated-secret>
GUNICORN_WORKERS=2
TZ=Europe/Paris
```

### HTMX Integration

The web UI uses HTMX for task toggle. Route `/tasks/<int:task_id>/toggle` (app/routes_main.py:233) detects HTMX requests via `HX-Request` header and returns partial HTML (`task_item.html`).

### API Behavior

- **POST /api/tasks**: Returns 201 (created), 409 (duplicate), or 400 (validation error)
- **GET /api/tasks**: Supports query params: `from`, `to`, `is_done`, `limit`, `offset`
- Order: open tasks first, then by `display_order`, `due_date`, `created_at DESC`

### Weekend Task Generation

When the script runs on Friday morning, it calculates the target weekend and generates tasks with proper `due_date` based on `day_offset`:
- `day_offset=0` → Friday
- `day_offset=1` → Saturday
- `day_offset=2` → Sunday

## Deployment Notes

The repository includes `DEPLOIEMENT_SIMPLE.md` with deployment instructions for LXC Proxmox containers with Tailscale. Key points:

- Service runs as systemd unit (`todo-hotel.service`)
- Logs rotate via `RotatingFileHandler` (10MB max, 5 backups)
- Weekly cron job for task generation (Fridays 06:00)
- Weekly database backups (Sundays 02:00)
- Healthcheck endpoint: `/healthz`

## Testing Guidelines

When writing tests:
- Use in-memory SQLite: `SQLALCHEMY_DATABASE_URI="sqlite://"`
- Create fixtures for the Flask app and database
- Test edge cases for weekend calculations (Monday/Friday transitions)
- Verify duplicate prevention in `create_task_if_not_exists`
- Mock external API calls in script tests
- Cover all HTTP status codes for API endpoints
