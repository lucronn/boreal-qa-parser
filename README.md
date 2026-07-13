# Boreal QA Parser & Alignerr PR Dashboard

A beautiful, feature-rich command-line tool to query, monitor, and parse pre-flight/QA findings for pull requests in the Alignerr repositories under the `Alignerr-Code-Labeling` organization.

It extracts detailed findings from Boreal, Taiga, and general Trusted CI comment feedback, formatting them into an easy-to-read, color-coded terminal dashboard.

## Installation

You can install this tool using `uv` or `pip`:

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/lucronn/boreal-qa-parser.git
cd boreal-qa-parser

# Install dependencies and build locally
uv pip install -e .
```

Alternatively, run it directly without installing via `uv`:
```bash
uv run boreal-cli list
```

## Features & Usage

### Authentication
The CLI automatically retrieves your GitHub credentials using your local `gh` token configuration. Alternatively, you can set the `GITHUB_TOKEN` environment variable:
```bash
export GITHUB_TOKEN="your_personal_access_token"
```

### 1. List All PRs
Displays a high-level dashboard table showing all PRs, their states, CI decisions, Boreal grade, and finding counts.

```bash
boreal-cli list
```

Options:
- `--repo <repo_name>`: Filter by a specific Alignerr repository name (e.g. `zzpop04gg` or full name).
- `--state [open|closed|all]`: Filter PRs by state (default is `all`).

```bash
boreal-cli list --state open
```

### 2. View PR Details & Boreal Findings
Displays complete details of a specific pull request, including:
- Overall CI grade decision and next actions.
- Specific files and required fixes.
- Grader QA details (Grade, Score, Min Axis Score, Model summary).
- Parsed Boreal pre-flight findings with rule identifiers and suggested fixes.

```bash
boreal-cli view <repo_name> <pr_number>
```
*Note: You can use the short suffix for repository names (e.g., `zzpop04gg` instead of the full `lbx-rl-tasks-iso-efbb2b18-gh-task-zzpop04gg`).*

```bash
boreal-cli view zzpop04gg 12
```

## License
MIT