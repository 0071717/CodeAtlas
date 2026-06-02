You are acting as a repository health-check agent for a CodeAtlas extraction framework.

Task:
Read `atlas/config/project.yaml`, verify the configured frontend and backend repository paths exist, and inspect their high-level structure.

Do not extract requirements yet.

Write:
- atlas/global/repo-health-report.md
- atlas/global/repo-health.json

Check and report:
- whether frontend path exists
- whether backend path exists
- detected frontend framework and package manager
- detected backend framework and package manager
- whether `node_modules`, `.venv`, `dist`, `build`, `.next`, `.pytest_cache`, or other generated folders exist
- likely routing style in frontend
- likely API client style in frontend
- likely state management libraries
- likely validation libraries
- likely backend router structure
- likely backend schema/model structure
- likely backend service/repository structure
- likely test frameworks
- obvious risks for context bloat
- recommended exclude paths for analysis

Rules:
- Do not analyze business logic yet.
- Do not create a domain map yet.
- Prefer factual filesystem observations.
- If a path is missing, clearly explain which config value is wrong.
