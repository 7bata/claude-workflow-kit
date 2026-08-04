# claude-workflow-kit

English | [中文](README.zh-CN.md)

A documentation-driven multi-agent development workflow for Claude Code: **Conductor / Executor / Reviewer three-tier division of labor** + **brainstorming → spec → ultracode straight-through implementation** + **the eight-doc set project documentation system**.

Contains two parts:

1. **A workflow prompt** (below in this README) — drop it into your `~/.claude/CLAUDE.md` to define the model division of labor, the tier table, and the main workflow
2. **A Claude Code plugin** (`plugins/workflow-en/`) — provides two executable commands:
   - `/scaffold`: lay down the methodology scaffolding in place in your project (`.claude/CLAUDE.md` + the eight-doc set + `.gitignore` + `README.md`)
   - `/whats-next`: read the docs to figure out where the project stands and what to do next

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
- **Evals included** (`plugins/speak-human*/evals/`): 22 sanitized real failure cases + a per-rule rubric + a baseline-vs-skill runner (`run_evals.py`), so rule edits can be regression-tested instead of vibes-tested.

## Usage (project lifecycle)

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
| `docs/REQUIREMENTS.md` | Product requirements, **single source of truth** — change requirements here first |
| `docs/BUSINESS.md` | Business profile: business facts (how things were done before the system, business rules) — change business rules here first |
| `docs/PLAN.md` | Phased roadmap + Phase status (✅) + Spec Index; holds only the index, not the full text |
| `docs/Progress.md` | Module status overview table + changelog (newest first) |
| `docs/DECISIONS.md` | Key decision records, each with What/Why/Changes, newest first |
| `docs/ARCHITECTURE.md` | Tech stack, architecture diagrams, data model, API, directory structure |
| `docs/DEPLOYMENT.md` | Deployment shape, environment variables, startup commands |
| `docs/MEETINGS.md` | Raw archive of meeting notes + action items; conclusions get distilled into the docs above |

## Customizing the tech-stack baseline

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
2. **`xhigh` / `max` never enter batch stages.** Reserve them for the rare single-point decision: the hardest one-shot verdict, a security audit — judgment calls where a mistake is expensive. If a review wants more confidence, add votes (3 votes of `opus` + `medium`) rather than escalating a single vote to xhigh, **and each vote must use a different lens: correctness / security / boundary and malformed data — never three votes rereading the same prompt. Homogeneous votes share blind spots; vote count is not confidence.** That's the whole point of the Workflow adversarial-verification pattern.
3. **Consequence overrides difficulty.** Any unit touching irreversible operations or a large blast radius — data migrations, deleting/overwriting data, auth and permissions, payments, public releases — gets an `opus` + `high` review no matter how low its implementation tier is, and the review checklist must include "a rollback path exists and is executable". Implementation tiers still follow difficulty; only the verification gets more expensive.
4. **Empirical calibrations have a shelf life.** The empirical conclusions in the tier table (opus for frontend, medium as the starting tier, etc.) are dated calibrations that expire when a new model generation ships: rerun a retrospective on your session usage data — if medium's rejection rate is <5%, consider probing down to `low`; >30% means the starting tier is too low. Change the table based on data, not vibes.

## 4. Batch work goes through Workflow, not bare Agent

`effort` is only supported by the Workflow script's `agent()`; the bare Agent tool has no such parameter — subagents dispatched that way can only inherit the main session's tier and can't be lowered. So batch/parallel tasks should always go through Workflow orchestration first — don't fork off with a bare Agent. Every `agent()` in a Workflow script writes `model` + `effort` explicitly per stage according to the tier table; orchestration logic and final synthesis never go inside the workflow — they're done by the main conversation itself.

## 5. Git branch & backup strategy

1. **Branch means push**: day-to-day development always happens on a feature/wip branch — switch to or create one before starting work (a worktree flow satisfies this automatically); push the current branch to the remote immediately after every commit, no confirmation needed (use `-u` to set upstream if there isn't one yet) — this is your real-time offsite backup.
2. **main is gated**: the confirmation checkpoint is at **merging into the default branch**, not at pushing. Merging into main (or committing directly on main) requires the user's confirmation first; after confirmation, push main and delete the merged remote feature branch.
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
     - `REQUIREMENTS.md` — Product Positioning, Target Users, Phased Roadmap, Confirmed Decisions (fill in with real content from intake wherever possible)
     - `BUSINESS.md` — business profile: how things were done before the system, business rules, input/output sample registry (fill in with what the 7-slot checklist collected)
     - `ARCHITECTURE.md` — architecture design; `DEPLOYMENT.md` — deployment plan
     - `DECISIONS.md` — decision records, each with What/Why/Changes, **newest first** (the tech-stack baseline is the first entry)
     - `MEETINGS.md` — meeting-notes archive + an action-item list per section
4. **Wrap-up**: `git init` (if not already) + initial commit; self-check for unreplaced placeholders and mangled text; report to the user what was generated and what decisions were made, and suggest moving on to the brainstorming flow in Section 7.

## 7. Main workflow: Brainstorming → Spec → Ultracode straight-through

1. All creative work starts with superpowers:brainstorming, writing the design spec to `docs/superpowers/specs/<date>-<topic>-design.md` and registering it in the Spec Index of `docs/PLAN.md`.
2. Writing the spec constitutes a standing authorization for this round of Workflow multi-agent implementation (ultracode): **don't wait for approval, don't ask "should I start implementing", don't invoke superpowers:writing-plans, don't produce an implementation plan document** — move straight into implementation automatically (if the user explicitly asks to stop mid-flow, stop as usual).
3. If isolation is needed, create a worktree first (superpowers:using-git-worktrees, or the Workflow agent's `isolation: 'worktree'`).
4. Workflow-orchestrated implementation: first output a 3-5 line **kickoff summary** (how many units, each unit's model/effort tier, estimated scale) — **don't wait for confirmation, start right away**; the summary just gives the user a visible interrupt window. Then break the spec into independent units → parallel implementation agents (`sonnet`, each following TDD, with a self-contained prompt: attach the relevant spec section + the project's CLAUDE.md hard rules) → dispatch a review agent (`opus`) to verify and rule on each unit as it completes — besides the implementation, the reviewer must also examine **the tests themselves** (do they cover the spec's acceptance criteria; do they only test the happy path); weak tests count as a rejection, and a rejected unit's re-run splits tests and implementation across two agents → main conversation synthesizes and fixes.
5. After implementation, proceed as usual through superpowers:requesting-code-review → verification-before-completion → finishing-a-development-branch; wherever these skills have a "plan" placeholder (e.g. PLAN_OR_REQUIREMENTS), fill it with the spec path. Once done, update `docs/Progress.md` (status table + changelog) and `docs/PLAN.md` (mark the Phase ✅).
6. This workflow overrides the brainstorming SKILL.md rule that "the only skill you invoke after brainstorming is writing-plans"; subagent-driven-development / executing-plans lose their entry point since there's no longer a plan document — that's expected, no need to work around it to satisfy them.
7. When the user explicitly names writing-plans / subagent-driven / inline / parallel dispatch, execute in the way named.

## 8. Do GitHub research first for new products / major features

- **New product/new project: research is mandatory**, no "should we research" decision step.
- **Larger features: Claude's judgment call** (signals: needs a new subsystem or standalone module, the domain clearly has mature open-source options, expected effort is large; ask the user if unsure).
- **Timing**: after brainstorming intent is clear, before proposing candidate solutions.
- **Method**: research mature open-source implementations on GitHub (use a dedicated research skill if one exists; otherwise use web/GitHub search to achieve equivalent research).
- **Output**: the research conclusion (adopt/self-host directly, fork and customize, build in-house + reusable components) must be presented as one of the formal candidate solutions, and captured in the spec's "Prior art" section.
- Small tweaks don't trigger this; skip if the user explicitly says "no need to research".

## 9. Continuity: ask "what's next" when returning to a project (corresponds to /whats-next)

When the user says "what's next / where am I", and the project root has a `docs/PLAN.md`:

1. **The docs are the sole source of truth** — don't traverse the codebase just to answer this question; only spot-check code when the docs contradict each other and need cross-checking.
2. Read, in order: `PLAN.md` (roadmap + Phase status + Spec Index) → `Progress.md` (status table + the last 2-3 log entries) → the latest spec (check against Progress to determine whether it's already implemented) → the last 2-3 entries of `DECISIONS.md` → the action items in the latest section of `MEETINGS.md`.
3. **Judge in order, stop at the first match**:
   | State | Next step |
   |---|---|
   | The latest spec isn't implemented yet | Implement directly from that spec with ultracode; if unsure whether the spec has been approved, ask first |
   | All specs implemented, but PLAN.md still has un-✅ Phases | Run brainstorming for the next Phase to produce a new spec → ultracode (skip writing-plans), register the spec in the Spec Index |
   | PLAN.md's roadmap is still TBD | Read the Phased Roadmap in REQUIREMENTS.md as input first, use brainstorming to define the phased roadmap |
   | All Phases are ✅ | The project is complete as planned; suggest a retrospective or starting a new Phase |
4. **Output four parts**: ① Where you are (what was most recently completed, citing the date of the latest Progress entry); ② Next step (task name + the first action down to the file/command level + its source); ③ Watch-outs (decisions and pitfalls from DECISIONS/Progress in the same domain as the next step, with sources cited; omit if none); ④ Meeting action items not yet in any plan (unchecked items in the latest MEETINGS section that haven't entered any plan yet, prompting the user to decide where they go; omit if none). End by asking: start now?
5. If the docs contradict each other (e.g. Progress says done but the spec has no implementation record) → clearly point out the contradiction and both sides' sources, and suggest reconciling before proceeding — **never silently pick one**; if `PLAN.md`/`Progress.md` are missing, that means this isn't a project under this workflow — suggest running Section 6's scaffolding first.
```

## Repo structure

```
claude-workflow-kit/
├── README.md                        # English README (default front page)
├── README.zh-CN.md                  # Chinese README: methodology + install + workflow prompt
├── LICENSE                          # MIT
├── .claude-plugin/
│   └── marketplace.json             # Plugin marketplace manifest
└── plugins/
    ├── workflow/                     # Chinese-output plugin
    │   ├── .claude-plugin/plugin.json
    │   └── skills/
    │       ├── scaffold/             # /scaffold: SKILL.md + templates/ (11 templates)
    │       │   ├── SKILL.md
    │       │   └── templates/
    │       │       ├── CLAUDE.md.tmpl  README.md.tmpl  gitignore.tmpl
    │       │       └── docs/         # the eight-doc set templates
    │       └── whats-next/           # /whats-next: SKILL.md
    │           └── SKILL.md
    ├── workflow-en/                  # English-output plugin (same layout as workflow)
    │   ├── .claude-plugin/plugin.json
    │   └── skills/
    │       ├── scaffold/              # /scaffold: SKILL.md + templates/ (11 templates)
    │       │   ├── SKILL.md
    │       │   └── templates/
    │       │       ├── CLAUDE.md.tmpl  README.md.tmpl  gitignore.tmpl
    │       │       └── docs/         # the eight-doc set templates
    │       └── whats-next/           # /whats-next: SKILL.md
    │           └── SKILL.md
    ├── speak-human/                  # Chinese speak-human plugin
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/speak-human/SKILL.md   # asking discipline P1–P8 + speaking discipline S1–S3
    │   ├── hooks/                    # SessionStart hook, flag-file gated always-on
    │   └── evals/                    # 22 sanitized cases + rubric + baseline-vs-skill runner
    └── speak-human-en/               # English speak-human plugin (same layout)
```

## License

[MIT](LICENSE)
