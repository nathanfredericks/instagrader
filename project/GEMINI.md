# InstaGrader

## Project Overview
InstaGrader is a Django-based platform designed to assist teachers in grading student essays using AI. It provides a structured way to manage assignments, define detailed rubrics, and process student submissions with automated grading and feedback capabilities.

**Key Features:**
*   **Assignments:** Create and manage writing prompts and assignments.
*   **Rubrics:** Define customizable grading rubrics with specific criteria and levels.
*   **Grading:** Automated grading of essays based on defined rubrics, with support for teacher overrides and approval.
*   **API:** Fully documented REST API for frontend integration.

## Technologies & Architecture
*   **Backend Framework:** Django 6.0.2
*   **API Framework:** Django Rest Framework (DRF) 3.16+
*   **Authentication:** JWT (via `rest_framework_simplejwt`)
*   **API Documentation:** OpenAPI 3.0 (via `drf-spectacular`)
*   **Database:** SQLite (default for development)
*   **Python Version:** >= 3.14

### Key Apps
*   **`instagrader`**: Project settings and root URL configuration.
*   **`accounts`**: User management and authentication.
*   **`assignments`**: Core domain logic for `Assignment` creation and `Essay` submissions.
*   **`rubrics`**: Management of `Rubric`, `RubricCriterion`, and `CriterionLevel` definitions.
*   **`grading`**: Logic for `GradingResult` and `CriterionScore`, linking essays to rubric scores.

## Building and Running

### Prerequisites
*   Python 3.14 or higher
*   `uv` (recommended) or `pip`

### Installation
1.  **Install Dependencies:**
    ```bash
    uv sync
    # OR
    pip install -r requirements.txt  # (if generated from pyproject.toml)
    ```

2.  **Apply Migrations:**
    ```bash
    python manage.py migrate
    ```

3.  **Run Development Server:**
    ```bash
    python manage.py runserver
    ```

### Testing
Run the full test suite:
```bash
python manage.py test
```

Run tests for a specific app:
```bash
python manage.py test assignments
```

## Development Conventions

### Code Style
*   Follow **PEP 8** standards.
*   **Django Conventions:** Use standard project layout (apps at root).
*   **Naming:**
    *   Classes: `CamelCase` (e.g., `AssignmentSerializer`)
    *   Variables/Functions: `snake_case` (e.g., `calculate_score`)
    *   Constants: `UPPER_CASE`

### Data Models
*   **Primary Keys:** All models use `UUIDField` as the primary key (`id`).
*   **Foreign Keys:** strict usage of `on_delete` policies (e.g., `PROTECT` for rubrics to prevent accidental deletion of used criteria).
*   **Ordering:** Models have explicit `ordering` Meta options (usually by creation date).

### API & Documentation
*   API endpoints are prefixed with `/api/`.
*   Swagger UI is available at `/api/docs/`.
*   Redoc is available at `/api/redoc/`.
*   Keep `drf-spectacular` schema definitions up to date.

### File Structure
```text
/
├── instagrader/        # Project settings
├── accounts/           # User & Auth
├── assignments/        # Assignments & Essays
├── grading/            # Grading logic & Results
├── rubrics/            # Rubric definitions
├── manage.py           # CLI entry point
├── pyproject.toml      # Dependencies & Metadata
└── db.sqlite3          # Dev database
```
