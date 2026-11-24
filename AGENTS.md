# Repository Guidelines

## Project Structure & Module Organization

GreenRoute estimates journey emissions and recommends sustainable travel. Backend development is moving to FastAPI.

- `FastApi/main.py` contains the GreenRoute app and health endpoint.
- `FastApi/index.py` contains a separate books API used for learning FastAPI.
- `FastApi/data/` holds sample journey requests, route responses, and emission factors.
- `Main/server.js` contains the earlier Express implementation. `Main/Services/carbon-calculator.js` contains JavaScript calculation examples.
- `Ui images/` and `Class diagram and flowchart/` contain reference PDFs. `PROJECT_PLAN.md` describes planned milestones and includes earlier technology choices.

## Build, Test, and Development Commands

Run commands from the repository root unless specified.

- `python -m venv .venv` creates a local Python environment. In PowerShell, activate it with `.\.venv\Scripts\Activate.ps1`.
- `python -m pip install fastapi uvicorn` installs the current Python server dependencies. A dependency manifest has yet to be added.
- `python -m uvicorn FastApi.main:app --reload` starts GreenRoute locally. Open `/docs` for interactive API testing.
- `python -m uvicorn FastApi.index:app --reload` runs the books practice API separately.
- `node --check Main/server.js` checks JavaScript syntax. To install JavaScript dependencies, run `npm ci` inside `Main/`.

The Express server currently references `Main/data/`, while fixtures reside in `FastApi/data/`. Resolve those paths before running it.

## Coding Style & Naming Conventions

Use four-space indentation and `snake_case` for Python functions and variables. Use `PascalCase` for request models. Preserve existing JSON field names such as `distanceKm` and `maxDurationMinutes`. For JavaScript, follow the existing two-space indentation and ES module imports. Prefer readable loops and short comments explaining calculations. Formatting and linting tools have yet to be configured.

## Testing Guidelines

Automated tests and coverage thresholds have yet to be configured. Test the health endpoint through `/docs` or Postman. As journey planning moves to Python, verify valid requests, invalid coordinates, unsupported modes, occupancy validation, bus-only journeys, and repeated requests. With current demo factors, expect 2.2 kg for an 11 km petrol trip with one occupant and 0.54 kg for a 9 km bus leg. Name future Python tests `test_*.py`.

## Commit & Pull Request Guidelines

History uses short messages, including `javascript version backend`. Write focused messages naming changed behaviour. Pull requests should explain changes, include verification results, reference relevant issues, and identify API or fixture changes.

## Emissions & Configuration

Label current factors as illustrative. Record units and sources when replacing them. Divide vehicle-kilometre factors by occupancy. Apply passenger-kilometre factors directly. Keep future provider keys in environment variables.
