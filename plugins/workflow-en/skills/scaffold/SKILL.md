---
name: scaffold
description: Lay down the methodology scaffolding in place inside the current project directory (CLAUDE.md + the seven-doc set + .gitignore + README). The backend stack is fixed to Go (version baseline in the table inside the skill); Claude decides the database based on project intent. Triggered when the user says "set up scaffolding / initialize project / start new project / scaffold".
allowed-tools: Bash, Read, Write, Glob, AskUserQuestion
---

# /scaffold

Lay down the methodology scaffolding in place, inside an **already-existing** project directory. **Respond in English by default** (technical identifiers stay in English).

Templates live in this skill's `templates/` subdirectory. When reading templates with Glob/Read, base the path off the skill's "Base directory for this skill" as given at invocation time, joined with `templates/` — do not hardcode an absolute path.

## Tech stack baseline (fixed, no selection process)

The backend stack is **fixed to Go**, with version and library choices unified under the baseline below (a fixed baseline is part of this methodology: no re-deciding per project; if you want to change the stack, edit this table rather than deviating once, ad hoc):

| Component | Choice / Version | Notes |
|---|---|---|
| Backend language | Go 1.25 (built via `golang:1.25-alpine`) | Standard library `net/http` + chi router, no heavyweight framework |
| DB access | pgx (hand-written repository) | No ORM, no sqlc — `internal/repo` writes typed SQL directly |
| Migrations | golang-migrate | Pure SQL versioned migrations (`NNNN_*.up.sql / down.sql`) |
| Validation / serialization | `encoding/json` + go-playground/validator | Request/response schema validation |
| Frontend (if needed) | React + TypeScript + Vite | `node:20-alpine` used only at build stage |
| Runtime image | `alpine:3.20` | Docker multi-stage build, single static binary, `/health` health check |
| Directory layout | `backend/cmd/server` entrypoint + `backend/internal/{config,db,repo,handlers,service,model,middleware}` | Go community convention; frontend under `frontend/src` |

Keep the backend service **stateless** (all state lives in the database), leaving room for horizontal scaling across multiple replicas.

## Step 1: Confirm project name and directory

```bash
basename "$PWD"
```
Take the current folder name as the project name. Confirm the current directory is indeed the project root to be scaffolded.

## Step 2: Intake — gather project intent

Explain to the user and collect:

> Tell me the idea for this project / a meeting summary, or point me to a file (e.g. meeting notes `*.md`) — I'll use it to determine the tech stack, database, core invariants, and module breakdown.

- If the user gives a file path → Read it; if it's **meeting notes**, archive the raw content into the first section of `docs/MEETINGS.md` when writing to disk
- If the user describes it verbally → use the conversation content
- If there isn't enough information to decide, ask **targeted** follow-up questions (not generic ones)

## Step 3: Decide and confirm

Based on the intake, list the following items for the user along with your reasoning, and use AskUserQuestion to have the user confirm/revise:

1. **Backend tech stack** — **fixed to Go, no question asked, no selection process** (see the "Tech stack baseline" table at the top). Only **state** to the user that this baseline will be used; if the user actively asks to switch stacks, treat it as a signal to update this skill's baseline table rather than deviating just this once
2. **Database**:
   - **PostgreSQL by default** (for concurrency / most scenarios; Go side uses pgx + golang-migrate, per the baseline table)
   - **SQLite only for small, low-concurrency / single-machine appliances** (e.g. a mac mini appliance)
   - Basis for the decision: concurrency level, deployment shape (cloud vs. single machine), data scale
3. **Whether a web frontend is needed**: if yes, follow the baseline React + TypeScript + Vite; for pure API / CLI projects, no frontend directory
4. **Core invariants**: 0–N architectural constraints this project must "never break." Leave a placeholder if you can't think of any yet
5. **Module breakdown**: top-level module names + one-line responsibility each. Leave a placeholder if unclear

State the **reasoning** behind each item, and let the user sign off. Only write to disk after confirmation.

## Step 4: Write to disk (with conflict protection)

First list the 10 target files to be written, and **check each one for existence**:

```bash
for f in .claude/CLAUDE.md docs/PLAN.md docs/Progress.md docs/ARCHITECTURE.md docs/DEPLOYMENT.md docs/REQUIREMENTS.md docs/DECISIONS.md docs/MEETINGS.md .gitignore README.md; do
  test -e "$f" && echo "EXISTS: $f"
done
```

- If any `EXISTS` show up → list them and ask the user: skip / back up and rename (`.bak`) / manually merge. **Never overwrite silently**
- If no conflicts → proceed

For each template: Read the template content → substitute placeholders → Write to the target path. Placeholder substitution table:

| Placeholder | Value source |
|---|---|
| `{{PROJECT_NAME}}` | Folder name from Step 1 |
| `{{ONE_LINER}}` | One-line positioning distilled from intake |
| `{{DATE}}` | `date +%F` |
| `{{TECH_STACK}}` | Fixed baseline: `Go 1.25 (net/http + chi) + pgx + golang-migrate`; if there's a frontend, append `; frontend React + TypeScript + Vite (Node 20 build)` |
| `{{DATABASE}}` | Database from Step 3 |
| `{{INVARIANTS_BLOCK}}` | Core invariants from Step 3; if none, `<!-- TBD: this project's core invariants -->` |
| `{{MODULES_BLOCK}}` | Module breakdown from Step 3; if none, `<!-- TBD: module breakdown -->` |
| `{{CODE_CONVENTIONS_BLOCK}}` | Go code conventions generated from the baseline (Go 1.25, gofmt, explicit error handling with wrapping, `cmd/` + `internal/` layout, minimal dependencies); if there's a frontend, append TS conventions (strict mode, components organized by page directory) |

Template path mapping: `templates/docs/X.md.tmpl` → `docs/X.md`; `templates/gitignore.tmpl` → `.gitignore`; `templates/CLAUDE.md.tmpl` → `.claude/CLAUDE.md`; `templates/README.md.tmpl` → `README.md`. Also create an empty placeholder directory `data/.gitkeep`.

**Pre-filling content** (don't just substitute placeholders — fill in real content wherever possible):

- `docs/REQUIREMENTS.md`: fill in as much real content as possible from what intake distilled (Product Positioning, Target Users & Roles, Phased Roadmap, Confirmed Decisions); leave a TBD comment for anything that can't be filled in
- `docs/MEETINGS.md`: if intake came from meeting notes, archive the raw notes as the first section; otherwise keep the empty skeleton
- `docs/DECISIONS.md`: the template comes with a "Go baseline" first entry; if Step 3 produced other significant decisions (e.g. rationale for choosing SQLite), append a What/Why/Changes entry for each

## Step 5: Wrap-up

```bash
git rev-parse --git-dir >/dev/null 2>&1 || git init
git add -A
git commit -m "chore: initialize project scaffold"
```

After writing to disk, **self-check**:
```bash
grep -rl '{{' .claude docs README.md 2>/dev/null && echo "⚠ Unreplaced placeholders remain" || echo "All placeholders replaced ✓"
LC_ALL=C grep -rl $'\xef\xbf\xbd' .claude docs README.md 2>/dev/null && echo "⚠ Garbled text found" || echo "No garbled text ✓"
```

Report to the user: which files were generated, the tech stack/DB decisions, and next-step suggestions (`/brainstorming` to start design — once the spec is approved, go straight into ultracode implementation, or just start working directly).
