#!/bin/sh
# auto-scaffold standing injection (plugin edition): injected by default,
# only skipped when the opt-out flag file exists.
# This is the opposite direction from speak-human's opt-in (flag file
# present -> inject) -- this rule's target users are vibe-coding users who
# wouldn't proactively flip a switch on, so installing the plugin is treated
# as opting into the methodology; the misfire guardrail lives in the
# conservative judgment logic inside the rule body itself (better to miss
# than to misfire), not in the switch.
# touch ~/.claude/.auto-scaffold-off to disable globally (delete the file to re-enable).

# Evals isolation switch: the claude -p subprocess that eval runs spawn
# carries this env var, and the hook stays silent and injects nothing --
# otherwise the "baseline" arm would also pick up the rule from the hook
# when a standing user runs an eval, breaking the two-arm comparison
# (mirrors speak-human).
[ -n "${AUTO_SCAFFOLD_EVALS_HERMETIC:-}" ] && exit 0

FLAG="${HOME}/.claude/.auto-scaffold-off"
[ -f "$FLAG" ] && exit 0

RULE="${CLAUDE_PLUGIN_ROOT}/hooks/auto-scaffold.md"
[ -f "$RULE" ] || exit 0

# The rule body has no YAML frontmatter, so it's emitted as-is, no stripping needed.
cat "$RULE"
