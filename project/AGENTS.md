# Repository Guidelines

## Project Structure & Module Organization
- `instagrader/` contains Django project configuration (settings, ASGI/WSGI, root URLs).
- Domain apps live at the repo root: `accounts/`, `assignments/`, `grading/`, `rubrics/`.
- App code follows standard Django layout: `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`.
- Tests are colocated per app in `*/tests.py`.
- `manage.py` is the main entry point for management commands.
- `db.sqlite3` is a local development database snapshot.

## Build, Test, and Development Commands
- `python manage.py runserver` starts the local development server.
- `python manage.py migrate` applies database migrations.
- `python manage.py makemigrations` generates new migration files after model changes.
- `python manage.py test` runs the Django test suite.
- Dependencies are defined in `pyproject.toml` (Python >= 3.14). If you use `uv`, install with `uv sync`.

## Coding Style & Naming Conventions
- Follow PEP 8 for Python formatting and Django conventions for app layout.
- Use `snake_case` for functions/variables, `CamelCase` for classes, and `UPPER_CASE` for module constants.
- Keep API endpoints and serializers named consistently with their app domain (e.g., `AssignmentSerializer`, `RubricViewSet`).
- No formatter/linter is configured; keep diffs clean and readable.

## Testing Guidelines
- Use Django’s built-in `TestCase` in `*/tests.py`.
- Name tests with `test_*` and keep each test focused on one behavior.
- Run the full suite with `python manage.py test`; run a single app with `python manage.py test accounts`.

## Commit & Pull Request Guidelines
- Commit messages are short, descriptive summaries (e.g., “Implement authentication”).
- PRs should include a clear summary, testing notes (commands run), and any migration implications.
- If a change affects API behavior, call it out explicitly and update relevant app `urls.py` or serializers.

## Configuration & Data Notes
- Treat `db.sqlite3` as a local dev artifact; avoid relying on it for production behavior.
- Do not commit secrets or credentials; use environment variables and `instagrader/settings.py` defaults responsibly.
