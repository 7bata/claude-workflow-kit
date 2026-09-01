# claude-workflow-kit

English | [中文](README.zh-CN.md)

A documentation-driven multi-agent development workflow for Claude Code: **Conductor / Executor / Reviewer three-tier division of labor** + **brainstorming → spec → ultracode straight-through implementation** + **the eight-doc set project documentation system**.

Contains two parts:

1. **A workflow prompt** (below in this README) — drop it into your `~/.claude/CLAUDE.md` to define the model division of labor, the tier table, and the main workflow
2. **A Claude Code plugin** (`plugins/workflow-en/`) — provides three executable commands plus three capabilities:
   - `/scaffold`: lay down the methodology scaffolding in place in your project (`.claude/CLAUDE.md` + the eight-doc set + `.gitignore` + `README.md`)
   - `/whats-next`: read the docs to figure out where the project stands and what to do next
   - `/sop-generate`: generate a screenshot-backed business SOP (operating manual) for an already-deployed web app
   - **Goal ledger**: every requirement you voice in conversation gets logged the same round into the inbox section of `docs/REQUIREMENTS.md`; brainstorming reconciles against it, wrap-up settles it, `/whats-next` reports what's still open — so requirements stop evaporating between batches
   - **docs-capture**: three standing hooks that keep the decision log honest — every AskUserQuestion answer is deterministically captured into `docs/DECISIONS.inbox.md`, free-text decision/requirement phrasing triggers a soft reminder, and a commit gate nudges you to digest pending drafts (see the "docs-capture" section below)
   - Plus a standing capability: **auto-scaffold** — new sessions auto-recognize "the user wants to build something new" and silently create the folder + git repo + scaffolding (on by default, opt-out available; see the "Auto-scaffolding new projects" section below)

## Install

```
/plugin marketplace add 7bata/claude-workflow-kit
/plugin install workflow-en@claude-workflow-kit
```

This repo ships two plugin variants — install **one** of them:
- `workflow-en@claude-workflow-kit` — English output (this README)
- `workflow@claude-workflow-kit` — Chinese output

Their skills share the same `/scaffold` and `/whats-next` command names, so installing both at once would collide — pick the one that matches your output language.

Then copy the entire "Workflow prompt" section below into `~/.claude/CLAUDE.md` (global effect) or your project's `.claude/CLAUDE.md` (project-only effect).

### Dependencies

| Dependency | Purpose | Notes |
|---|---|---|
| Claude Code (with the Workflow orchestration tool, i.e. ultracode) | Multi-agent orchestration, specifying `model`/`effort` per stage | The execution substrate for the workflow |
| [superpowers plugin](https://github.com/obra/superpowers) | brainstorming / TDD / code review / worktree and other process skills | The skeleton of the main workflow; see its README for install instructions |

The main conversation should use the strongest model currently available (e.g. Fable/Opus) as the "Conductor".

## Bonus plugin: speak-human

Make Claude speak human and ask answerable questions. The rules are mined from 548 real AskUserQuestion decision records (67% picked as-is / 16% absorbed-then-synthesized / 12% declined into chat): a pre-question self-check (verify the premise with tools first, brief the why/state/impact, gloss every piece of jargon, don't force false either/or — leave room to combine, one decision point per round, real previews for visual calls) plus three expression rules (follow the user's language, gloss jargon everywhere, no file-name roll call as narration).

```
/plugin install speak-human-en@claude-workflow-kit   # English version
/plugin install speak-human@claude-workflow-kit      # Chinese version (install one, not both)
```

- **On demand**: trigger with `/speak-human` in any session.
- **Always on**: `touch ~/.claude/.speak-human-always` — a SessionStart hook injects the rules into every session automatically; delete the file to turn it off.
- **Evals included** (`plugins/speak-human/evals/`): 43 sanitized/synthesized failure cases (13 verified + 8 unverified + 22 early unlabeled) + a per-rule rubric + a baseline-vs-skill runner (`run_evals.py`), so rule edits can be regression-tested instead of vibes-tested.

## Bonus plugin: send-to

`/send-to <session-name> <what to relay>` — relay a message to another Claude Code session on the same machine, built on cross-session messaging (Claude Code v2.1.224+, macOS/Linux; sending has no built-in slash command, which is why this skill exists). What it pins down:

- **Fuzzy name matching**: auto-generated session names are mostly "dirname-2char" (e.g. `myapp-ec`); typing just "myapp" works. On zero or multiple hits it shows you the live session list and asks instead of guessing.
- **Self-contained messages**: the receiving session has none of your context, so the relay must carry the background, the specifics (branches, commits, paths), and the expected action — never "as we discussed".
- **Honest delivery reporting**: "sent" never gets inflated into "they got it"; when permission modes differ between sessions the message is held at the receiver for approval, and the skill relays that state truthfully.
- **Cross-profile discovery is invisible but direct send works, and an identity registry tells you who's who**: cross-session discovery is isolated per profile (each session only registers in its own profile's registry) — windows opened under another profile are mutually invisible in `ListAgents`, but `SendMessage` with an explicit `uds:` address reaches across accounts directly (verified by a controlled experiment on 2026-08-10), no longer a fringe last resort. To fix the "I can see a socket but can't tell whose it is" problem, `send-to`'s SessionStart hook voluntarily registers this session's identity (project name, account, profile, start time, launch command line) into a shared identity registry; on zero hits the skill reads that registry first and works through a four-tier ladder (`ListAgents` → identity registry direct send → the existing address-source ladder → file handoff) to find the target, sending directly without detours whenever the target is uniquely identified. **This hook must be installed and active in every profile to register that profile's sessions** — skip a profile and its windows can only be found via the address ladder or file handoff. Registration is on by default; `touch ~/.claude/.cc-session-registry-off` disables it globally (delete the file to re-enable). File handoff (a self-contained handoff file plus a one-line paste command the user drops into the target window) is now the true last resort, triggered only when the entire four-tier ladder comes up empty.

```
/plugin install send-to-en@claude-workflow-kit   # English version
/plugin install send-to@claude-workflow-kit      # Chinese version (install one, not both)
```

## Bonus plugin: ui-sweep

Before SOP screenshots, or as a regression sweep after a batch of UI changes, systematically click every interactive element on the site — driven by `vercel-labs/agent-browser` (a Rust CLI with bundled Chrome for Testing, a11y snapshots with element references) plus a self-built generalized traversal engine: inject login state → walk the screen list defined in the project's `sweep.config.mjs` → per screen, restore the baseline state, click each element in turn and observe, log to a eight-category ledger (state changed / no reaction / dialog dismissed / click error / page error / denylisted / target lost / left-domain recovered) → emit a JSONL ledger, a screenshot per screen, and a report.

- **Externalized config**: `node sweep.mjs <path>/sweep.config.mjs` reads the project's `ROOT`/`SCREENS` (required) plus `DENY_EXTRA`/`ensureBaseline`/`OUT` (optional); missing required fields fail fast instead of silently running an empty sweep.
- **Safety boundary**: the default denylist (revoke/dissolve/delete/log out/logout/archive/clear/reset/send/save/upload, etc.) can only be appended to via `DENY_EXTRA`, never trimmed by a project; destructive buttons are logged, never clicked; `confirm`/`prompt` dialogs are always dismissed, never producing a real write; two-layer domain guard: `--allowed-domains` restricts explicit navigation only (click-driven jumps get through — empirically verified, so the engine takes over session lifecycle), while the reliable layer is the engine's per-click hostname check — leaving the domain is logged as `left-domain` and the scene is restored on the spot; only for sites you own or are authorized to test.
- **`--strict` mode**: restores the baseline state after every single click, fixing the false-positive where accumulated on-screen state masks a later click's effect; off by default (full sweeps run roughly 2x slower with it on) — use the default mode for first passes, and `--strict` to re-verify a `dead` list.
- **Orphan-feature audit (optional)**: a sweep can only find "there's a button and clicking it does nothing"; it can't find "the feature shipped but the frontend has no entry point at all" — that takes an audit. Give the config an `INVENTORY` (backend API + frontend route lists, generated on the spot by Claude for your stack) and the engine collects the requests actually triggered during the sweep, diffs them against the inventory, and reports `unreachable` (probably no entry point) / `broken-entry` (entry exists but returns 4xx/5xx) / `exempt` (webhooks and friends, expected to have no UI entry) — with four families of false-positive triage guidance (permissions / data state / denylist / incomplete coverage) and a three-condition test for a real orphan. **With no `INVENTORY` configured the whole audit stays silent and behaviour is byte-for-byte what it was before.**

```
/plugin install ui-sweep-en@claude-workflow-kit   # English version
/plugin install ui-sweep@claude-workflow-kit      # Chinese version (install one, not both)
```

## Bonus plugin: Workflow Kit for Codex CLI

The same documentation-driven workflow, ported for the OpenAI Codex CLI: `plugins/workflow-codex/` (packaged as a `.codex-plugin/plugin.json`, not a Claude Code plugin — install it through whatever skill/plugin mechanism your Codex CLI build uses). It targets `AGENTS.md` instead of `.claude/CLAUDE.md` and ships **five** skills:

- `scaffold`: lay down the methodology scaffolding (`AGENTS.md` + the eight-doc set + `.gitignore` + `README.md`)
- `whats-next`: read the docs to figure out what to do next
- `sop-generate`: generate a screenshot-backed business SOP for an already-deployed web app
- `parallel-do`: split a step into independent subtasks and fan them out to parallel Codex subagents — this one is Codex-only, standing in for Claude Code's native multi-agent orchestration tool
- `speak-human`: makes Codex follow the same say-it-like-a-human discipline for asking and speaking — a port of the same P1–P9/S1–S6 rules from the "Bonus plugin: speak-human" section below, with always-on persistence reworked to write into `~/.codex/AGENTS.md` (see the "always-on install" section at the end of that skill file for the script)

`workflow-codex` does **not** auto-trigger scaffolding on install the way the Claude Code version does — Codex CLI has no session-start hook mechanism, so installing the plugin alone won't make it recognize "I want to build a new thing" and lay down scaffolding automatically. To get that behavior, opt in manually by following the "Auto mode and always-on install (optional)" section at the end of the `scaffold` skill file: it walks you through writing the trigger rule into `~/.codex/AGENTS.md` (idempotent install/uninstall scripts included, safe to re-run).

### Installing workflow-codex

```
git clone <this repo's URL> ~/claude-workflow-kit
codex plugin marketplace add ~/claude-workflow-kit
codex plugin add workflow-codex@claude-workflow-kit
```

The marketplace manifest already lives at `.agents/plugins/marketplace.json` in this repo — `marketplace add` just needs to point at the local repo root after cloning (pointing it directly at a git URL hasn't been verified to work, so it isn't recommended here).

### Run mode (read this first)

Codex's default `workspace-write` sandbox excludes `.git` from what's writable — `git init` / `git commit` both fail with `Operation not permitted`. This workflow makes an atomic commit after every operation, so `.git` needs write access before anything else works. `read-only` mode won't run at all. Both options below have been verified working:

1. **Recommended (smallest exposure window — verified for both `git init` and `git commit`)**: stay in `workspace-write`, and just add this project's `.git` to the writable roots —

   ```
   codex -s workspace-write -c 'sandbox_workspace_write.writable_roots=["/abs/path/to/project/.git"]'
   ```

   or set it in `~/.codex/config.toml` (can live in a per-project profile):

   ```toml
   [sandbox_workspace_write]
   writable_roots = ["/abs/path/to/project/.git"]
   ```

   This also works before `.git` exists yet (verified with an empty directory: both `git init -b main` and the first commit exit 0), so it covers scaffold's first-run case too.

2. **For one-off / containerized / CI environments**, a coarser switch works: `codex -s danger-full-access`; for non-interactive batch runs, `codex exec --dangerously-bypass-approvals-and-sandbox`. Only use these in a project directory you trust.

Run a quick self-check before starting — pass it before you begin, don't wait until scaffold is half-done to find out:

```
git commit --allow-empty -m probe && git reset --hard HEAD~1
```

### Where the Codex version and the Claude version diverge

- **Where specs live**: Codex has no superpowers plugin, so design specs live at `docs/specs/YYYY-MM-DD-<topic>-design.md`, not the Claude-side `docs/superpowers/specs/` used below
- **Who drives parallel implementation**: once a spec is finalized, `parallel-do` handles the parallel implementation, not the ultracode / Workflow multi-agent orchestration tool below
- **Where to edit the tech-stack baseline**: edit `plugins/workflow-codex/skills/scaffold/SKILL.md` and its `templates/`, not `plugins/workflow-en/` as the "Customizing the tech-stack baseline" section below points to
- **No docs-capture hooks**: the three-layer decision/requirement capture described in Section 6b (`AskUserQuestion` → `DECISIONS.inbox.md`, signal-word reminders, commit-time gate) is not ported here — it depends on Claude Code's hooks mechanism, which Codex CLI doesn't have. The discipline still stands (log decisions and requirements before they evaporate); on the Codex side it's enforced by convention, not automation.

## Usage (project lifecycle)

> The paths and orchestration tool below are **Claude-version conventions**; see "Where the Codex version and the Claude version diverge" above for Codex.

```
New project          Returning to a project
    │                     │
/scaffold            /whats-next ──→ tells you the next step
    │                     │
    ▼                     ▼
brainstorming ──→ design spec (docs/superpowers/specs/)
   │
   ▼
ultracode (Workflow multi-agent orchestration) implements directly from the spec
   │  sonnet implements in parallel (TDD) + opus reviews each unit + main conversation summarizes
   ▼
code review → verification → wrap-up, write back to docs/Progress.md and docs/PLAN.md
```

Responsibilities of each file in the eight-doc set:

| File | Responsibility |
|---|---|
| `docs/REQUIREMENTS.md` | Product requirements, **single source of truth** — change requirements here first; contains the "Goal Ledger (inbox)" section collecting requirements that surface in conversations/meetings |
| `docs/BUSINESS.md` | Business profile: business facts (how things were done before the system, business rules) — change business rules here first |
| `docs/PLAN.md` | Phased roadmap + Phase status (✅) + Spec Index; holds only the index, not the full text |
| `docs/Progress.md` | Module status overview table + changelog (newest first) |
| `docs/DECISIONS.md` | Key decision records, each with What/Why/Changes, newest first |
| `docs/ARCHITECTURE.md` | Tech stack, architecture diagrams, data model, API, directory structure |
| `docs/DEPLOYMENT.md` | Deployment shape, environment variables, startup commands |
| `docs/MEETINGS.md` | Raw archive of meeting notes + action items; conclusions get distilled into the docs above |

## Customizing the tech-stack baseline

> The path below is a **Claude-version convention**; see "Where the Codex version and the Claude version diverge" above for Codex.

`/scaffold` ships with a **fixed Go tech-stack baseline table** (Go + chi + pgx + golang-migrate, frontend React + TS + Vite). "Fix the baseline once, stop re-choosing per project" is part of the methodology; which specific stack you pick is a matter of personal preference — to swap in your own stack, edit the baseline table and corresponding `templates/` content in `plugins/workflow-en/skills/scaffold/SKILL.md`; the methodology itself doesn't change.

## Workflow prompt

> Copy the entire block below into `~/.claude/CLAUDE.md`. With this plugin installed, Section 6 is carried out by `/scaffold` and Section 9 by `/whats-next` — these two sections remain as the methodology write-up behind those commands. Without the plugin, you can still follow the description manually.

```markdown
# Multi-agent development workflow (Conductor / Executor / Reviewer three tiers + documentation-driven project lifecycle)

> Prerequisites: Claude Code, with the Workflow multi-agent orchestration tool (ultracode), and the superpowers plugin installed.
> The main conversation uses the strongest model currently available (e.g. Fable/Opus) as the "Conductor".
> This rule overrides the default model- and reasoning-effort-selection guidance in all skills (including every superpowers skill).

## 1. Three-tier division of labor (fixed)

| Role | Who does it | What it does |
|---|---|---|
| **Conductor** | Main conversation (strongest model) | Breaks down tasks, sets the approach, writes Workflow scripts, decides who to dispatch, does final synthesis and conflict adjudication; planning and architecture design always stay in the main conversation, never dispatched |
| **Executor** | `sonnet` subagent | Implementation/code changes/migrations/batch chores; read-only exploration/research |
| **Frontend artist** | `opus` subagent | Frontend visual/motion/UI polish: animation feel, layout look, bubble/overlay positioning, color and spacing — the "does it look right" kind of work (empirically, opus at medium tier beats sonnet here) |
| **Reviewer** | `opus` subagent | Code review, result verification, acceptance verdicts |

## 2. Tier table (both `model` and `effort` must be written explicitly — never omit either)

Omitting `model` inherits the main session's model; omitting `effort` inherits the main session's reasoning effort — if the main session is running at a high tier, mechanical work would run at that same depth, burning more money and time than picking the wrong model would.

| Stage type | model | effort |
|---|---|---|
| Locating files / listing / inventory | `haiku` or `sonnet` | `low` |
| Batch mechanical work: migration, renaming, templated code changes | `sonnet` | `low` |
| Regular implementation (TDD units) | `sonnet` | `medium` |
| Hard implementation: algorithms, concurrency, tricky bugs | `sonnet` | `high` |
| Frontend visual / UI polish | `opus` | `medium` |
| Single vote / refutation vote for quick verification in a review panel | `opus` | `medium` |
| Final review, acceptance verdict, security-related review | `opus` | `high` |
| Planning and architecture design | Not dispatched, stays in the main conversation | — |

## 3. Four principles for escalating/de-escalating tiers

1. **Escalate on failure — don't pay up front.** Implementation stages always start at `medium`; only escalate to `high` on a re-run when tests fail or the reviewer rejects a unit. In a batch of tasks, the hard ones are usually the minority — running everything at high makes the easy 90% subsidize the hard 10%, and the cost isn't just tokens, it's latency.
2. **`xhigh` / `max` never enter batch stages.** Reserve them for the rare single-point decision: the hardest one-shot verdict, a security audit — judgment calls where a mistake is expensive. If a review wants more confidence, add votes (3 votes of `opus` + `medium`) rather than escalating a single vote to xhigh, **and each vote must use a different lens: correctness / security / boundary and malformed data — never three votes rereading the same prompt. Homogeneous votes share blind spots; vote count is not confidence.** That's the whole point of the Workflow adversarial-verification pattern. Review orchestration comes in two shapes — pick based on the nature of the task: **parallel multi-vote** (the 3 votes with different lenses above — each vote independent, none seeing the others) fits acceptance rulings and correctness confirmation; **chained relay** fits diagnosis, root-causing, and troubleshooting — each round's review prompt explicitly attaches the prior round's conclusions and the hypotheses it already ruled out, so this round digs deeper on top of what came before instead of re-investigating from zero. Parallel votes each start from scratch, so they can't catch a case where "the prior round's conclusion itself was wrong" — chained rounds can; a good convergence rule for chaining is "two consecutive rounds with no new finding". Chained rounds inherit from one another — that doesn't count as padding the vote count.
3. **Consequence overrides difficulty.** Any unit touching irreversible operations or a large blast radius — data migrations, deleting/overwriting data, auth and permissions, payments, public releases — gets an `opus` + `high` review no matter how low its implementation tier is, and the review checklist must include "a rollback path exists and is executable". Implementation tiers still follow difficulty; only the verification gets more expensive. Red lines must also be **front-loaded onto the implementation side**: when dispatching implementation agents, write the production red lines into every prompt (see Section 7.4) — don't rely on review as the only backstop.
4. **Empirical calibrations have a shelf life.** The empirical conclusions in the tier table (opus for frontend, medium as the starting tier, etc.) are dated calibrations that expire when a new model generation ships: rerun a retrospective on your session usage data — if medium's rejection rate is <5%, consider probing down to `low`; >30% means the starting tier is too low. Change the table based on data, not vibes.

## 4. Batch work goes through Workflow, not bare Agent

`effort` is only supported by the Workflow script's `agent()`; the bare Agent tool has no such parameter — subagents dispatched that way can only inherit the main session's tier and can't be lowered. So batch/parallel tasks should always go through Workflow orchestration first — don't fork off with a bare Agent. Every `agent()` in a Workflow script writes `model` + `effort` explicitly per stage according to the tier table; orchestration logic and final synthesis never go inside the workflow — they're done by the main conversation itself.

## 5. Git branch & backup strategy

1. **Branch means push**: day-to-day development always happens on a feature/wip branch — switch to or create one before starting work (a worktree flow satisfies this automatically); push the current branch to the remote immediately after every commit, no confirmation needed (use `-u` to set upstream if there isn't one yet) — this is your real-time offsite backup.
2. **main is gated — only for changes the user can see in the frontend**: before merging into main (or committing directly on main), ask one question — could the user see or test the difference from the frontend? **Yes** (frontend code changes, or backend logic changes that alter frontend interaction/display behavior) → get the user's confirmation first, and when asking, show the changed page for inspection — merge all screenshots into one self-contained HTML (images embedded, opens directly in a browser, one caption line per image), deliver it in the conversation for direct viewing, and print its local file path in the reply so it can be pasted into a browser; a text description alone, or loose single screenshots, don't count; before delivering to the user, dispatch a visual-review subagent to inspect every screenshot one by one, hunting the defects anyone would spot at a glance — broken layout, overlapping elements, overflowing or clipped text, mojibake or placeholder text, blank or data-less regions, obviously missing styles, error messages; fix what it finds, re-screenshot, re-review, and only deliver once the review passes; when unsure whether something is a defect or intentional design, don't force a fix — flag it in the reply for the user to decide, and include a one-line review verdict (pass, or what was fixed); if the app cannot be run or the screenshots cannot be produced, stop the push and report the gate as blocked — never degrade to a text-only confirmation. **No** (anything the user can't test from the frontend: pure backend internals and refactors, docs, backend tests, scripts, CI, dependency bumps, changes that leave API behavior unchanged) → merge and push main directly, no confirmation needed — just report the merge to the user in one line. Either way, delete the merged remote feature branch as before; when unsure, treat it as "yes" and ask; committing directly on main is still governed by rule 1 (branch first) — this clause only decides whether to ask. This clause overrides finishing-a-development-branch's Step 4 three-option menu — on a "no" verdict, skip the menu, merge, and continue the wrap-up. The gate sits only where the user can verify with their own hands; for everything else the user has no way to check anyway, so asking is pure interruption.
3. **No-remote fallback**: if the repo has no remote (or the branch has no upstream), remind the user to set one up after the first commit, so "auto-push" doesn't silently fail.

## 6. Starting a new project: lay down doc scaffolding first (corresponds to /scaffold)

When the user says "new project / initialize project / set up scaffolding", lay it down in place inside an **existing** project directory (the project name is taken from the directory name). Process:

1. **Intake**: have the user describe the project idea, or point to a file (e.g. meeting notes); archive the raw notes into the first section of `docs/MEETINGS.md`, and separately distill any business facts they contain into `docs/BUSINESS.md`. Ask targeted follow-up questions if information is insufficient. Beyond deciding the tech stack/DB, **ask through a 7-slot business-context checklist** (used to fill in `docs/BUSINESS.md`; leave a placeholder for any slot with insufficient information — don't press the user or block the flow): ① goal & current manual process (before the system, who did it, how, where were the pain points); ② input: transactional data (is there a real sample file); ③ input: reference/config data (lookup tables, rule tables, allowed values); ④ processing flow (how input becomes output); ⑤ output (what's produced, for whom, is there a sample); ⑥ business hard rules & exceptions (rules that must never be violated, how exceptions are handled); ⑦ human review & feedback (who reviews, what can they change, should it be remembered by the system).
2. **Decide and confirm** (give a rationale for each decision; write to disk only after the user signs off):
   - **Tech stack: fixed baseline, no re-choosing.** Example baseline: Go (standard library `net/http` + chi, no heavy framework) + hand-written pgx repositories (no ORM) + golang-migrate plain-SQL migrations; frontend React + TypeScript + Vite if needed; Docker multi-stage build into a single static binary with `/health`; the backend is stateless, all state lives in the database. (Feel free to swap this table for your own baseline — the key point is "fix the baseline once, stop re-choosing per project"; if you want a different stack, change the baseline table, don't make a one-off exception.)
   - **Database**: PostgreSQL by default; SQLite only for small, low-concurrency, single-machine setups. Base the call on concurrency, deployment shape, and data scale.
   - **Whether a web frontend is needed.**
   - **Core invariants**: the architectural constraints this project must "never break", 0 to N of them; leave a placeholder if none come to mind.
   - **Module breakdown**: top-level module names + a one-line responsibility each; leave a placeholder if unclear.
3. **Write 11 files to disk** (check each one for existing presence first; for any that already exist, list them and ask the user to skip/back up/merge — **never overwrite silently**):
   - `.claude/CLAUDE.md` (project hard rules), `.gitignore`, `README.md`
   - **The eight-doc set**:
     - `PLAN.md` — Overall Roadmap, each Phase's status (title carries ✅ = done), Spec Index
     - `Progress.md` — top half: module status overview table (pending/doing/done); bottom half: changelog (**newest first**)
     - `REQUIREMENTS.md` — Product Positioning, Target Users, Phased Roadmap, Confirmed Decisions (fill in with real content from intake wherever possible) + the Goal Ledger (inbox) section
     - `BUSINESS.md` — business profile: how things were done before the system, business rules, input/output sample registry (fill in with what the 7-slot checklist collected)
     - `ARCHITECTURE.md` — architecture design; `DEPLOYMENT.md` — deployment plan
     - `DECISIONS.md` — decision records, each with What/Why/Changes, **newest first** (the tech-stack baseline is the first entry)
     - `MEETINGS.md` — meeting-notes archive + an action-item list per section
4. **Wrap-up**: `git init` (if not already) + initial commit; self-check for unreplaced placeholders and mangled text; report to the user what was generated and what decisions were made, and suggest moving on to the brainstorming flow in Section 7.

### 6a. Auto-scaffolding new projects (auto-scaffold)

For pure vibe-coding users who never type `/scaffold` and have no mental model of "a project is a folder": once the plugin is installed, a new session silently gets a standing rule injected at startup — when the user is describing "wanting to build something new" (not asking a question, not editing existing code) and the current directory is outside any git repo with no `docs/`/`.claude/`, it auto-creates the folder, runs `git init`, and lays down the eight-doc set via `/scaffold`'s Auto mode, then reports back in a single line and keeps working without waiting for confirmation. **The guiding principle is: when in doubt, don't act.** If it's unclear whether this counts as a new project, it does not trigger and work continues as normal; if the target directory already has a same-named file, it immediately downgrades to interactive mode and never overwrites silently.

- **Turning it off**: `touch ~/.claude/.auto-scaffold-off` disables it globally (the hook detects the flag and stops injecting the rule).
- **Changing the projects root**: write your preferred root path into `~/.claude/workflow-projects-root`; defaults to `~/Projects` if absent.
- **Trigger evals**: `plugins/workflow/evals/` (`cases.jsonl` + `run_evals.py` + `rubric.md`), covering trigger / no-trigger cases (15 total: 6 trigger, 9 no-trigger; the downgrade path is covered separately by a smoke test, not the evals set).
- **Still triggerable manually after opt-out**: touching the off-flag only disables silent auto-creation; the `/scaffold` command itself still works, whether typed manually or triggered by its own description.
- **No injection inside an existing git repo**: when the session's directory is already inside a git repo, the hook stops injecting this rule (condition 2 could never trigger anyway, so this saves context).

### 6b. Capturing decisions and requirements before they evaporate (docs-capture)

Verbal sign-offs and requirements said in passing tend to disappear once the conversation moves on — this is a three-layer hook mechanism that keeps them from being lost between sessions, layered so each catches what the previous layer misses:

1. **Layer 1 — deterministic capture** (`PostToolUse`, matcher `AskUserQuestion`): every time the user picks an option or types free text in an `AskUserQuestion` prompt inside a scaffolded project, a hook appends the raw Q&A verbatim to `docs/DECISIONS.inbox.md` — no summarizing, no judgment call, so nothing is lost to paraphrase. Silent outside project directories that have `docs/`.
2. **Layer 2 — signal reminder** (`UserPromptSubmit`, high-recall by design): scans each prompt you type against a decision-word list and a requirement-word list (`signals-decision.txt` / `signals-requirement.txt`); a third list, `signals-veto.txt`, holds question/undecided phrasings ("maybe", "not sure", "should we") that suppress a hit within the same clause — that's the file to tune if you see false positives. On a hit it nudges "this looks like a decision/requirement — worth logging" without blocking. Deliberately high-recall, not high-precision — it's a soft reminder layer, not a gate, so a false positive just costs a line of noise, not a blocked prompt.
3. **Layer 3 — commit gate** (`PreToolUse`, matcher: Bash commands containing `git commit`): before letting a `git commit` through, the hook checks (a) whether `docs/DECISIONS.inbox.md` still has undigested drafts (`## `-level entries), and (b) whether the staged change touches source files without touching `docs/Progress.md`. Either condition warns. The warn is "once per staged content, not once ever": it hashes the staged diff and compares against the last-warned hash; the same staged content is blocked the first time and let through if you rerun the identical commit unchanged (it does not verify the inbox was actually triaged — re-running the same commit as-is is what clears it).

Together the three layers turn "the user said it once and it vanished" into "it's on disk somewhere, and commit time forces a look" — Layer 1 guarantees capture, Layer 2 catches what happens outside an `AskUserQuestion` box, Layer 3 is the last-chance gate before it ships.

- **Turning it off**: all three layers share one kill switch — touch `~/.claude/.docs-capture-off` and every layer goes silent (there's no per-layer opt-out); for hermetic eval runs, set env var `DOCS_CAPTURE_EVALS_HERMETIC` to any non-empty value. Each layer also degrades independently on missing deps (e.g. no `jq` makes the scripts exit silently rather than error).
- **Triage, not free-form editing**: `docs/DECISIONS.inbox.md` is a raw buffer, not the source of truth — see the "文档同步规则" / doc-sync table in `CLAUDE.md.tmpl`: decisions get distilled into `docs/DECISIONS.md`, requirement-shaped entries move into the `docs/REQUIREMENTS.md` goal ledger, noise gets discarded.
- **Not ported to workflow-codex**: Codex CLI has no hooks mechanism to host these three layers on; the discipline (log it before it evaporates) still applies there, it's just enforced by convention, not automation (see the `workflow-codex` note in Section "Bonus plugin: Workflow Kit for Codex CLI").

## 7. Main workflow: Brainstorming → Spec → Ultracode straight-through

1. All creative work starts with superpowers:brainstorming, writing the design spec to `docs/superpowers/specs/<date>-<topic>-design.md` and registering it in the Spec Index of `docs/PLAN.md`. Before starting, read the `docs/REQUIREMENTS.md` goal ledger for items still in `open` state and list the ones relevant to this round for the user; the spec must include a "**goal coverage statement**" — which ledger items this round covers, and which it explicitly does not, with reasons.
2. Writing the spec constitutes a standing authorization for this round of Workflow multi-agent implementation (ultracode): **don't wait for approval, don't ask "should I start implementing", don't invoke superpowers:writing-plans, don't produce an implementation plan document** — move straight into implementation automatically (if the user explicitly asks to stop mid-flow, stop as usual).
3. If isolation is needed, create a worktree first (superpowers:using-git-worktrees, or the Workflow agent's `isolation: 'worktree'`).
4. Workflow-orchestrated implementation: first output a 3-5 line **kickoff summary** (how many units, each unit's model/effort tier, estimated scale) — **don't wait for confirmation, start right away**; the summary just gives the user a visible interrupt window. End the kickoff summary with a ready-to-paste goal command: `/goal "Complete <batch/spec name>" until "<key acceptance criteria from the spec or the ledger items this batch covers> are all satisfied"` — `/goal` is a Claude Code session-scoped built-in command (it auto-evaluates the completion condition every turn, guarding against long sessions drifting off track); it doesn't persist across sessions — persistence across batches relies on the goal ledger. Then break the spec into independent units → parallel implementation agents (`sonnet`, each following TDD, with a self-contained prompt: attach the relevant spec section + the project's CLAUDE.md hard rules + **production red lines and file ownership** — FORBIDDEN FILES (name the files/directories this unit must not touch), never restart shared services, never read or write production data, no force push and no history rewrite that discards changes, touch only the files assigned to this unit) → dispatch a review agent (`opus`) to verify and rule on each unit as it completes — besides the implementation, the reviewer must also examine **the tests themselves** (do they cover the spec's acceptance criteria; do they only test the happy path); weak tests count as a rejection, and a rejected unit's re-run splits tests and implementation across two agents → main conversation synthesizes and fixes. Review reports must always **report deltas, not summaries**: only report what's new or overturned relative to the prior round and to other votes — no "checked it, looks fine" recaps; if there's nothing new, say so explicitly and list the checkpoints that were re-verified. Choose review orchestration by task: acceptance rulings use parallel multi-lens votes; diagnosis/root-cause/troubleshooting use chained relay (each round's prompt attaches the prior round's conclusions and the hypotheses it ruled out; converge only after two consecutive rounds with no new finding — see Section 3.2).
5. When this batch touches UI (frontend pages/interactions), run a ui-sweep interaction regression scan before code review (systematically click through every interactive element site-wide), and bring the dead (clicked, no response) / page-error / left-domain list into acceptance review; only rule a real defect after per-item verification in a real browser, and classify false positives (accumulated state, blocking synchronous prompts, buttons that are the current-state control) per the skill's interpretation guide. Skip for backend-only or docs-only batches. After implementation, proceed as usual through superpowers:requesting-code-review → verification-before-completion → finishing-a-development-branch; wherever these skills have a "plan" placeholder (e.g. PLAN_OR_REQUIREMENTS), fill it with the spec path. Once done, update `docs/Progress.md` (status table + changelog) and `docs/PLAN.md` (mark the Phase ✅), and at the same time settle the goal ledger — mark this batch's covered items `done` with evidence (commit/screenshot/spec clause), and register any new goals that surfaced during implementation. If this batch produced a **reusable building block that other projects could pick up** (a general-purpose middleware, data pipeline, LLM client, deployment template, parser, etc. — not business-specific logic), register it at wrap-up in your organization's component index (the same one §8's Step 0 looks up; if you don't have one, start from a single YAML list with fields like slug/name/capability/repo/path/how_to_integrate/maturity/since/used_by), **verifying the real paths before you write them**, then push the entry back to whatever repo holds that index. This closes the loop with "Step 0: internal first": one looks the index up, this one creates the entries — an index everybody reads and nobody writes decays into a stale list within months.
6. This workflow overrides the brainstorming SKILL.md rule that "the only skill you invoke after brainstorming is writing-plans"; subagent-driven-development / executing-plans lose their entry point since there's no longer a plan document — that's expected, no need to work around it to satisfy them.
7. When the user explicitly names writing-plans / subagent-driven / inline / parallel dispatch, execute in the way named.

### 7a. Wording conventions for security-hardening work

For security/hardening work — specs, dispatch prompts, code comments, commit messages — always describe **what the system does** in neutral engineering language (input validation, rate limiting, session expiry, permission tightening), not "what/whom it defends against". If a threat scenario genuinely needs to be recorded, put it in human-facing project docs (`DECISIONS.md` / `BUSINESS.md`), not in dispatch prompts or code comments. Reason: adversarially-framed messages can get an entire message blocked by content-safety classifiers, forcing a spec rewrite or a model switch — a pitfall hit repeatedly across real sessions. This is wording engineering, not concealment: the same hardening action is expressed just as completely when described as "system behavior".

### 7b. Log requirements to the ledger the same round (goal-ledger logging rule)

Any requirement, expectation, or complaint the user expresses in conversation — even a single sentence — must be logged into the "goal ledger" in `docs/REQUIREMENTS.md` **the same round** (date + verbatim quote + source), followed by a one-line reply "Logged to the goal ledger." When unsure whether something counts as a requirement, log it as `open` anyway — better to over-log than to miss one; **failing to log it counts as not having heard it, and is forbidden.** Requirement-type items from meeting notes and user feedback likewise land in the ledger first and get promoted later; action items (things to do) still go to PLAN/spec, not the ledger.

## 8. Do GitHub research first for new products / major features

- **New product/new project: research is mandatory**, no "should we research" decision step.
- **Larger features: Claude's judgment call** (signals: needs a new subsystem or standalone module, the domain clearly has mature open-source options, expected effort is large; ask the user if unsure).
- **Timing**: after brainstorming intent is clear, before proposing candidate solutions.
- **Step 0: internal first (a hard step)**: check **your own organization** for reusable building blocks first — a component index, existing projects/modules on internal code hosting (e.g. a self-hosted GitLab); internal hits are presented **side by side** with external open-source candidates for the user to decide — never silently preferred or excluded just for being internal. If the internal index is unavailable, record that honestly and continue with external research without blocking.
- **Method**: research mature open-source implementations on GitHub (use a dedicated research skill if one exists; otherwise use web/GitHub search to achieve equivalent research).
- **Output**: the research conclusion (adopt/self-host directly, fork and customize, build in-house + reusable components) must be presented as one of the formal candidate solutions, and captured in the spec's "Prior art" section.
- Small tweaks don't trigger this; skip if the user explicitly says "no need to research".
- **Periodic audit**: do a full pass over the component index once a quarter or at each generation shift: fill gaps (things built but not registered), clear stale entries (paths deleted / projects archived — flag or remove), and re-check whether `maturity` still holds. An index that never gets audited degrades into a stale list — checking it is then equivalent to not checking it.

## 9. Continuity: ask "what's next" when returning to a project (corresponds to /whats-next)

When the user says "what's next / where am I", and the project root has a `docs/PLAN.md`:

1. **The docs are the sole source of truth** — don't traverse the codebase just to answer this question; only spot-check code when the docs contradict each other and need cross-checking.
2. Read, in order: `PLAN.md` (roadmap + Phase status + Spec Index) → `Progress.md` (status table + the last 2-3 log entries) → the latest spec (check against Progress to determine whether it's already implemented) → the last 2-3 entries of `DECISIONS.md` → the action items in the latest section of `MEETINGS.md` → the `open` items in the `REQUIREMENTS.md` goal ledger.
3. **Judge in order, stop at the first match**:
   | State | Next step |
   |---|---|
   | The latest spec isn't implemented yet | Implement directly from that spec with ultracode; if unsure whether the spec has been approved, ask first |
   | All specs implemented, but PLAN.md still has un-✅ Phases | Run brainstorming for the next Phase to produce a new spec → ultracode (skip writing-plans), register the spec in the Spec Index |
   | PLAN.md's roadmap is still TBD | Read the Phased Roadmap in REQUIREMENTS.md as input first, use brainstorming to define the phased roadmap |
   | All Phases are ✅ | The project is complete as planned; suggest a retrospective or starting a new Phase |
4. **Output five parts**: ① Where you are (what was most recently completed, citing the date of the latest Progress entry); ② Next step (task name + the first action down to the file/command level + its source); ③ Watch-outs (decisions and pitfalls from DECISIONS/Progress in the same domain as the next step, with sources cited; omit if none;if this batch touched UI and Progress has no ui-sweep record, note here that a follow-up interaction regression scan is recommended — omit and don't push if not applicable)); ④ Meeting action items not yet in any plan (unchecked items in the latest MEETINGS section that haven't entered any plan yet, prompting the user to decide where they go; omit if none); ⑤ Unsettled goals (items still `open` in the REQUIREMENTS.md goal ledger, listed one by one, flagging any pending more than 7 days at the top; omit if none). End by asking: start now?
5. If the docs contradict each other (e.g. Progress says done but the spec has no implementation record) → clearly point out the contradiction and both sides' sources, and suggest reconciling before proceeding — **never silently pick one**; if `PLAN.md`/`Progress.md` are missing, that means this isn't a project under this workflow — suggest running Section 6's scaffolding first.
```

## Repo structure

```
claude-workflow-kit/
├── README.md                        # English README (default front page)
├── README.zh-CN.md                  # Chinese README: methodology + install + workflow prompt
├── LICENSE                          # MIT
├── .claude-plugin/
│   └── marketplace.json             # Plugin marketplace manifest (registers eight plugins)
└── plugins/
    ├── workflow/                     # Chinese-output plugin
    │   ├── .claude-plugin/plugin.json
    │   ├── hooks/                    # auto-scaffold standing rule (hooks.json + inject.sh + auto-scaffold.md) + docs-capture (capture-decisions.sh, signal-reminder.sh, commit-gate.sh, signals-decision.txt, signals-requirement.txt, signals-veto.txt, docs-capture-smoke-test.sh)
    │   ├── evals/                    # auto-scaffold trigger evals: cases.jsonl + run_evals.py + rubric.md + .gitignore (out/, __pycache__/)
    │   └── skills/
    │       ├── scaffold/             # /scaffold: SKILL.md (with Auto mode section) + templates/ (11 templates)
    │       │   ├── SKILL.md
    │       │   └── templates/
    │       │       ├── CLAUDE.md.tmpl  README.md.tmpl  gitignore.tmpl
    │       │       └── docs/         # the eight-doc set templates
    │       ├── whats-next/           # /whats-next: SKILL.md
    │       │   └── SKILL.md
    │       └── sop-generate/         # /sop-generate: SKILL.md + references/ + scripts/
    │           ├── SKILL.md
    │           ├── references/       # runbook-template.md (degraded-delivery template for unreachable networks)
    │           └── scripts/          # crawl.mjs (native Playwright fallback collection script)
    ├── workflow-en/                  # English-output plugin (same layout as workflow, incl. matching hooks/)
    ├── workflow-codex/                # OpenAI Codex CLI port (five skills, no Claude Code plugin manifest)
    │   ├── .codex-plugin/plugin.json
    │   └── skills/
    │       ├── scaffold/             # AGENTS.md + the eight-doc set (no CLAUDE.md.tmpl)
    │       ├── whats-next/
    │       ├── sop-generate/
    │       ├── parallel-do/          # Codex-only: fan a step out to parallel Codex subagents
    │       └── speak-human/          # ported say-it-like-a-human discipline, persists via ~/.codex/AGENTS.md
    ├── speak-human/                  # Chinese speak-human plugin
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/speak-human/SKILL.md   # asking discipline P1–P9 + speaking discipline S1–S6
    │   ├── hooks/                    # SessionStart hook, flag-file gated always-on
    │   └── evals/                    # 33 sanitized cases + rubric + baseline-vs-skill runner
    ├── speak-human-en/               # English speak-human plugin (same layout)
    ├── send-to/                      # Chinese send-to plugin: relay a message to another local session
    │   ├── .claude-plugin/plugin.json
    │   ├── hooks/                    # SessionStart registration hook: writes this session's identity to the shared registry
    │   └── skills/send-to/SKILL.md   # fuzzy target matching + self-contained message rules + honest delivery reporting
    ├── send-to-en/                   # English send-to plugin (same layout)
    ├── ui-sweep/                     # Chinese ui-sweep plugin: agent-browser-driven full UI interaction sweep
    │   ├── .claude-plugin/plugin.json
    │   └── skills/ui-sweep/
    │       ├── SKILL.md              # env self-check → login-state injection → screen inventory → run the engine → read results → write the report
    │       ├── scripts/              # sweep.mjs (generalized traversal engine) + export-state.mjs (login-state export)
    │       └── references/           # report-template.md (report skeleton)
    └── ui-sweep-en/                  # English ui-sweep plugin (same layout; scripts byte-identical to the Chinese version)
```

## License

[MIT](LICENSE)
