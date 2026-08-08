---
name: send-to
description: Use when the user types /send-to <session-name> [content], or asks to relay/forward something to another Claude Code session on this machine ("tell the other window/terminal about this").
argument-hint: [target session name] [what to relay; omit to use what just happened in this conversation]
---

# send-to — relay a message to another Claude Code session on this machine

Built on Claude Code's cross-session messaging: `ListAgents` lists the local peer sessions, `SendMessage` delivers plain text by name. The receiver gets only that text — **none of this session's history, files, or context**.

## Requirements

- Claude Code v2.1.224+, macOS/Linux (not available on native Windows). If `/list-agents` isn't recognized in a session, that session doesn't have the feature.
- Neighboring commands: `/list-agents` (alias `/peers`) shows reachable sessions; `/rename` names a session (only a named session can be resumed with `claude --resume <name>`). Sending itself has no built-in slash command — which is exactly why this skill exists.

## Steps

1. **Load the tool**: `SendMessage` is a deferred tool — load it first with `ToolSearch("select:SendMessage")`, or a direct call fails with InputValidationError. `ListAgents` needs no loading.
2. **Find the target**: get the list from `ListAgents`, then match the first word of the arguments case-insensitively: exact → prefix → substring. Listed names are mostly auto-generated as "dirname-2char" (e.g. `hapi-ec`); users often remember only "hapi" — that's normal input, not an error.
   - **Exactly 1 hit** → proceed, no extra confirmation needed.
   - **0 or ≥2 hits** → show the user the full list (name, status, started) and let them pick via AskUserQuestion. Never pick "the most likely one" on their behalf, and never go digging through tmux / processes / the other session's screen to identify it — the listing is the only legitimate source of information.
3. **Compose the message (self-containment is a hard rule)**: the receiver shares no context with this session; the message must stand alone:
   - Background: which project, what this is about;
   - Substance: branch names, commit ids, paths, conclusions spelled out in full — never "as we discussed" or "the plan from earlier";
   - Expected action: what the receiver should do, and whether a reply is needed.
   - If the user gave no content (`/send-to hapi` and nothing else) → take the obvious thing to relay from the current conversation; if unsure what to relay, ask first.
4. **Send**: `SendMessage({to: "<name>", summary: "<5-10 word summary>", message: "<body>"})`.
   - The first message to a given peer may fail with an error asking for a `[ref]` confirmation (e.g. `hapi-ec [226d36]`) — the error message shows the exact form to use; **resend copying it verbatim**. This is not a fault.
5. **Report honestly**: a successful send only means the message went out — report "sent", never "they received/read it". When the two sessions' permission-mode classes differ, the message is **held** at the receiver pending that user's approval; the hold notice arrives asynchronously, possibly after you report — so **absence of a notice never justifies claiming "it wasn't held"**. When a hold notice does arrive, relay it honestly: "the message is held at the receiving session and needs approval in that window (or that session sets crossSessionInbound to accept)" — and never spam resends over it.

## Boundaries

- Entries labeled Remote Control (your sessions on other machines or on the web) are **reply-only — you cannot initiate**. If the match lands on one, explain that to the user instead of forcing a send.
- To continue a whole conversation or share full context, use `claude --resume <name>`, not a message; for big files or long history, send the path and let the receiver read it itself.
- Permission boundary: never use a message to get another session to do something this session was denied or would be blocked from doing.

## Common mistakes

| Symptom | Fix |
|---|---|
| SendMessage fails with InputValidationError | Tool not loaded via ToolSearch — back to step 1 |
| Error asks for a [ref] | Resend copying the exact form from the error — see step 4 |
| Multiple hits, picked one and sent anyway | Violation. Back to step 2: show the list, ask |
| Message contains "as discussed earlier" | Not self-contained — rewrite per step 3 |
| Reporting "they got it" / "it wasn't held" after a successful send | Say "sent" only; hold notices arrive async — relay one when it comes (step 5) |
