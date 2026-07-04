# Technical Debt Inventory - Bomi Project

This inventory document of technical-debt-related items in the `bomi` repository was compiled by analyzing current source files, testing patterns, and file layouts.

## Found Markers (TODO/FIXME)
A deep search of all files under development (source files, test suites, markdown files, configuration, and documentation) revealed **0 occurrences** of explicit `TODO` or `FIXME` markers.

## Unstaged or Untracked Files
`git status` reports that the working tree is clean. There are no untracked temporary files or build artifacts cluttering the workspace.

## Proposed Review Areas for Technical Debt
To conduct a thorough housekeeping analysis, we partition the project into the following distinct review areas:

### Area 1: API, Scraper, & Analysis Core
- **Path Focus:** `src/bomi/api.py`, `src/bomi/analysis.py`, `src/bomi/scrape.py`
- **Focus:** LLM API integration with OpenRouter, robust scraping logic with custom bracket parsing, and potential error/concurrency/rate-limiting/timeout handling.

### Area 2: Command-Line Interface (CLI)
- **Path Focus:** `src/bomi/cli.py`
- **Focus:** Structure of Click commands, handling of user options, output formatting, helper boundaries, and error boundaries.

### Area 3: Data Store & Models
- **Path Focus:** `src/bomi/db.py`, `src/bomi/models.py`, `src/bomi/project.py`, `src/bomi/config.py`
- **Focus:** SQLite database management, caching logic, data normalization, configurations, and project settings file handling.

### Area 4: Utilities & Filters
- **Path Focus:** `src/bomi/filters.py`, `src/bomi/units.py`, `src/bomi/normalize.py`, `src/bomi/output.py`
- **Focus:** Parsing of SI units, sorting and comparisons of BOM attributes, filtering algorithms, and spreadsheet/markdown generation.
