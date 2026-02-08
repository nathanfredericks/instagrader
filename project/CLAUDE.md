# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
uv sync                              # Install dependencies
python manage.py runserver            # Start dev server
python manage.py migrate              # Apply migrations
python manage.py makemigrations       # Generate migrations after model changes
python manage.py test                 # Run full test suite
python manage.py test <app>           # Run tests for one app (accounts, rubrics, assignments, grading)
python manage.py test <app>.tests.<TestClass>           # Run a single test class
python manage.py test <app>.tests.<TestClass>.<method>  # Run a single test method
```

No linter or formatter is configured. Follow PEP 8 and keep diffs clean.

## Architecture

Django REST API for AI-powered essay grading. Python >= 3.14, Django 6.x, DRF with Simple JWT auth, Celery for async tasks. Frontend is a separate Next.js app at localhost:3000.

### Apps and Data Flow

- **accounts** — Custom User model (UUID PK, email as USERNAME_FIELD). JWT auth via `djangorestframework-simplejwt`.
- **rubrics** — Rubric → RubricCriterion (ordered) → CriterionLevel (score + descriptor). Owned by user.
- **assignments** — Assignment (linked to a rubric via PROTECT FK) → Essay (file upload + extracted text). Status workflow: DRAFT → GRADING → REVIEW → COMPLETED. Essay status: PENDING → PROCESSING → GRADED → REVIEWED.
- **grading** — GradingResult (OneToOne with Essay) → CriterionScore. Supports both AI-generated scores (level/feedback) and teacher overrides (teacher_level/teacher_feedback).

All models use UUID primary keys. Users can only access their own data.

### Key Patterns

- Most assignment and grading views are **stubs returning 501** — the API contracts (URLs, serializers, tests) are defined but views need implementation.
- Celery task `assignments.tasks.process_essay_batch` is a stub — intended to extract text from uploaded essay files.
- Essay upload supports single files, multiple files, and zip extraction. Filters out system files (.DS_Store, __MACOSX/, hidden files).
- Rubrics use PROTECT FK on assignments — a rubric cannot be deleted if any assignment references it.
- Tests use `@override_settings(MEDIA_ROOT='test_media/')` for file isolation and `Faker(seed=0)` for deterministic test data.
- Tests use DRF's `APITestCase` with shared mixins per app for user/data creation helpers.

### API Routes

```
/api/auth/          — accounts (register, login, refresh, me, change-password)
/api/rubrics/       — rubrics CRUD + nested criteria/levels
/api/assignments/   — assignments CRUD, upload, essays list, CSV/PDF export
/api/essays/        — essay detail, delete, grading, approve
/api/schema/        — OpenAPI schema
/api/docs/          — Swagger UI
```
