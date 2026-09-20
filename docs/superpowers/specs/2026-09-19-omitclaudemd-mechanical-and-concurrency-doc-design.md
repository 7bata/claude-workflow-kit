# Spec: omitClaudeMd for mechanical stages + document the Workflow concurrency env var

Date: 2026-09-19
Status: approved (Tony, 2026-09-19), ready for ultracode
Claude Code baseline: 2.1.278

## Goal coverage (目标覆盖声明)

- **Covers**: items 1 and 2 of the 2026-09-19 Claude Code changelog review
  (REQUIREMENTS ledger row 2026-09-19 "最近版本更新了…"):
  1. `omitClaudeMd` — mechanical workflow subagents skip the auto-loaded CLAUDE.md.
  2. `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS` — document the concurrency cap knob.
- **Explicitly not covered this batch**:
  - AGENTS.md adoption (changelog item 4) — YAGNI'd by Tony this batch.
  - New hook events / send-to delivery-notice update (changelog items 3, 5).
  - The idle-session reaper (separate task, policy already decided in the ledger).

## Background (verified facts)

- `omitClaudeMd` (Claude Code 2.1.271) suppresses, for a subagent, the auto-loaded
  CLAUDE.md at all levels (user `~/.claude/CLAUDE.md`, project `./CLAUDE.md` and
  parents, `CLAUDE.local.md`, nested). It does **not** suppress: the agent's own
  system prompt (the .md body), managed-policy CLAUDE.md, or any text injected into
  the prompt.
- It is set via agent-definition frontmatter `omitClaudeMd: true`, or via the CLI
  `--agents` JSON. It is **not** a direct option of the Workflow tool's `agent()`.
- The intended path to use it in a workflow: define a custom agent type (an agent
  `.md` with `omitClaudeMd: true`) and call it via `agent(prompt, { agentType: '...' })`.
  Composition of `agentType` + `omitClaudeMd` in a live Workflow run is "likely but
  unverified" per the feasibility check — see Verification.
- `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS` (1–256, 2.1.271/274) raises the
  Workflow per-run concurrent-agent cap. Default cap is about min(16, cores − 2).

## Change 1 — mechanical agent type with omitClaudeMd (mechanical stages only)

Scope decision (Tony): omitClaudeMd applies to **pure-mechanical stages only**
(locate / list / inventory; batch migrate / rename / template edits). Regular
implementation (sonnet) and all review (opus) agents keep CLAUDE.md.

### 1a. New agent definition
- New files: `plugins/workflow/agents/mechanical.md` (Chinese-output plugin) and
  `plugins/workflow-en/agents/mechanical.md` (English-output plugin). Creates a new
  `agents/` directory in each of those two plugins.
- Frontmatter: `name: mechanical`, `omitClaudeMd: true`, a one-line `description`,
  and `tools: Read, Grep, Glob, Edit, Write, Bash`.
- Body (system prompt), minimal, language matching the plugin: "You are a mechanical
  task executor for the workflow kit. Do exactly what the prompt instructs. Assume no
  project conventions beyond what the prompt provides. Every rule, constraint, and
  production red-line you must honor is included in the prompt itself."

### 1b. Rule / text updates
- Tier table (README §2 "Tier table", README.zh-CN §2, global CLAUDE.md 档位表,
  dev-toolkit WORKFLOW.md, huake variant): for the mechanical rows, add guidance to
  dispatch via `agent(prompt, { agentType: 'mechanical', model: 'sonnet'/'haiku',
  effort: 'low' })`, which skips the auto-loaded CLAUDE.md and saves tokens.
- Guardrail line (README §3/§4, README.zh-CN, global CLAUDE.md production-red-line
  rule, WORKFLOW.md): because the mechanical agent does not auto-load CLAUDE.md, any
  write-capable mechanical stage MUST carry the production red-lines and any needed
  hard rules in its own prompt. This is already required by the red-line rule and the
  ultracode dispatch step; this change only makes it explicit for mechanical stages.
- Scope note in the same place: only pure-mechanical stages use `agentType:
  'mechanical'`; regular implementation and all review agents keep CLAUDE.md.

## Change 2 — document CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS

- README §4 ("Batch work goes through Workflow"), README.zh-CN §4, global CLAUDE.md
  batch rule, dev-toolkit WORKFLOW.md, huake variant: document the env var (1–256):
  it raises the Workflow per-run concurrent-agent cap, default about min(16, cores−2).
  Caution to include verbatim in intent: raise it only when the machine has CPU and
  memory headroom; raising it on a loaded machine invites the overload seen on
  2026-09-19. No default change is made anywhere.

## Surfaces (mirror set)

1. Global `~/.claude/CLAUDE.md` — edited by the main conversation (Fable) directly,
   NOT delegated to a subagent, because it is the user's standing rules; edit only the
   tier-table and batch-work sections, nothing else.
2. Kit `README.md`
3. Kit `README.zh-CN.md`
4. `plugins/workflow` (agent def + any tier/batch text in its scaffold template / skills)
5. `plugins/workflow-en` (agent def + any tier/batch text in its scaffold template / skills)
6. dev-toolkit `WORKFLOW.md` (and its mirrored plugin copies, if any)
7. huake variant (locate the huake claude plugin's workflow text at implementation time;
   if absent, report rather than invent a path)
- **Excluded**: `plugins/workflow-codex` — omitClaudeMd is Claude-Code-specific; the
  Codex variant uses AGENTS.md and a different tool. Leave it untouched.

## Verification

- **Smoke test (composition)**: create a throwaway project dir with a CLAUDE.md that
  defines one distinctive marker instruction (e.g., "always begin replies with the
  token ZZMARKER"). Run a one-agent workflow that calls `agent('State your first
  token.', { agentType: 'mechanical' })` and a control `agent(...)` without agentType.
  PASS if the mechanical agent does not emit ZZMARKER (CLAUDE.md was skipped) while the
  control does. If it does NOT compose, fall back: document the `--agents` JSON route
  and adjust the tier-table guidance to match; do not claim omitClaudeMd works via
  agentType if the test fails.
- **Consistency check**: the tier-table guidance, the guardrail line, and the env-var
  caution are equivalent in intent (language-appropriate) across all edited surfaces.

## Implementation units (for ultracode)

- **Unit 1 — agent definitions**: create `mechanical.md` in `plugins/workflow` and
  `plugins/workflow-en`. Mechanical. FORBIDDEN: any file outside those two agent files.
- **Unit 2 — kit README edits**: apply Change 1b + Change 2 to `README.md` and
  `README.zh-CN.md`. FORBIDDEN: any file outside those two.
- **Unit 3 — mirror edits (dev-toolkit + huake)**: apply Change 1b + Change 2 to
  dev-toolkit `WORKFLOW.md` (+ mirrored copies) and the huake variant. Work on a wip
  branch in each of those repos. FORBIDDEN: touching the kit repo or global CLAUDE.md.
- **Global CLAUDE.md edit**: done by the main conversation (Fable) directly, not a unit.
- **Unit 4 — smoke test**: implement and run the composition smoke test above; depends
  on Unit 1. Report PASS/FALLBACK.
- Each code/doc unit is reviewed by an `opus` agent. Unit 3 (mirror to shared repos)
  and the global CLAUDE.md edit are the higher-stakes surfaces; review at `opus` +
  `high` and confirm no unintended sections changed.

## Production red-lines (every unit's prompt must carry these)

- Only edit the files assigned to the unit; do not touch any other file.
- Do not restart shared services (HAPI hub/runner, DBs, etc.), do not read or write
  production data, do not force-push, do not rewrite history in a way that discards work.
- When editing README / WORKFLOW.md / CLAUDE.md, change only the tier-table, batch-work,
  and red-line sections named here; leave all other sections byte-for-byte unchanged.
