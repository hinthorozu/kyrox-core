# Cursor Development Rules

Cursor acts as the implementation developer.

## Mandatory Workflow

1. Read the assigned task file first.
2. Create a dedicated branch.
3. Modify only files required by the task.
4. Preserve DDD and Clean Architecture boundaries.
5. Write or update tests.
6. Run tests before reporting completion.
7. Push the branch.
8. Open a Pull Request.
9. Fill the PR template completely.

## Naming Rules

- Backend code must use English.
- Database tables, columns, indexes, constraints, and migrations must use English.
- API paths, request models, response models, and domain concepts must use English.
- Frontend user-facing labels, messages, errors, buttons, and UI text must use Turkish.

## Architecture Rules

- Domain layer must not depend on infrastructure.
- Domain entities must not import ORM, FastAPI, SQLAlchemy, Pydantic API schemas, or framework-specific code.
- Application layer coordinates use cases.
- Infrastructure implements repositories and external adapters.
- API layer exposes routes and maps requests/responses.
- Tests must protect architecture boundaries.

## Forbidden Actions

Cursor must not:

- Commit directly to main or develop.
- Rename large folders without explicit task instruction.
- Introduce cross-module imports without justification.
- Put business rules inside API routes.
- Put database concerns inside domain entities.
- Skip tests silently.
- Add unrelated refactors.
