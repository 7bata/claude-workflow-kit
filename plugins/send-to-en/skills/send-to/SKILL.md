---
name: send-to
description: Use when the user types /send-to <session-name> [content], asks to relay/forward something to another Claude Code session on this machine ("tell the other window/terminal about this"), or complains that another window doesn't show up in /list-agents or can't receive messages.
argument-hint: [target session name] [what to relay; omit to use what just happened in this conversation]
---

# send-to — relay a message to another Claude Code session on this machine

Built on Claude Code's cross-session messaging: `ListAgents` lists the local peer sessions, `SendMessage` delivers plain text by name. The receiver gets only that text — **none of this session's history, files, or context**.

## Requirements

- Claude Code v2.1.224+, macOS/Linux (not available on native Windows). If `/list-agents` isn't recognized in a session, that session doesn't have the feature.
- Neighboring commands: `/list-agents` (alias `/peers`) shows reachable sessions; `/rename` names a session (only a named session can be resumed with `claude --resume <name>`). Sending itself has no built-in slash command — which is exactly why this skill exists.
- **Cross-session discovery is isolated per login account** (verified bidirectionally, 2026-08-08): windows opened under different accounts/profiles (e.g. `CLAUDE_CONFIG_DIR` pointing at different directories, or an account switcher) are **mutually invisible and unreachable** — each session writes its registration file into its own profile's `sessions/` directory, and ListAgents reads only its own account's registry; only the socket directory `/tmp/cc-socks/` is shared, so "the socket exists but the list doesn't show it" is the fingerprint of a cross-account window. A session registers at startup (visible typically within tens of seconds) — whether it has ever spoken is irrelevant. This is a platform account boundary, not a fault. **SendMessage is the only delivery channel and ListAgents the only discovery channel**: never use any other means to get content into the other session yourself — writing to its socket, touching another profile's registration/session files, switching CLAUDE_CONFIG_DIR to spin up a relay session, taking the session over with `claude --resume` yourself, injecting keystrokes into its terminal via tmux/screen — all forbidden, however technically feasible. When unreachable, the only legitimate way out is the "File-handoff fallback" below — because the hands doing the crossing are the user's own.

## Steps

1. **Load the tool**: `SendMessage` is a deferred tool — load it first with `ToolSearch("select:SendMessage")`, or a direct call fails with InputValidationError. `ListAgents` needs no loading.
2. **Find the target**: get the list from `ListAgents`, then match the first word of the arguments case-insensitively: exact → prefix → substring. Listed names are mostly auto-generated as "dirname-2char" (e.g. `hapi-ec`); users often remember only "hapi" — that's normal input, not an error.
   - **Exactly 1 hit**: an exact or prefix hit → proceed, no extra confirmation; a hit found **only by substring** → show the user the full matched name for one confirmation before sending (so "hapi" can't silently land on "happy-xy"). All three levels empty means 0 hits — never loosen to fuzzy/edit-distance matching to manufacture a "hit".
   - **≥2 hits** → show the user the matching candidates (name, status, started) and let them pick via AskUserQuestion. Never pick "the most likely one" on their behalf, and never go digging through tmux / processes / the other session's screen to identify it — the listing is the only legitimate source of information.
   - **0 hits** → if the target window was opened moments ago, registration can lag by tens of seconds — re-run ListAgents once before judging. Still 0: check one thing before asking: `ls /tmp/cc-socks/` and count the live sockets. When sockets clearly outnumber "peer list entries + this session itself", there **may** be a window opened under another login account (mutually invisible and unreachable — see Requirements; it may also just be subagent or crashed-leftover sockets). Then lay the facts out for the user: the current list, plus whether surplus sockets exist, and offer two paths: (a) the target is actually one of the listed sessions / isn't open / the name is misremembered — pick one or go open it; (b) the target is another account's window — use the "File-handoff fallback". The socket count is a hint only: say "possibly", never state it as fact.
3. **Compose the message (self-containment is a hard rule)**: the receiver shares no context with this session; the message must stand alone:
   - Background: which project, what this is about;
   - Substance: branch names, commit ids, paths, conclusions spelled out in full — never "as we discussed" or "the plan from earlier";
   - Expected action: what the receiver should do, and whether a reply is needed.
   - If the user gave no content (`/send-to hapi` and nothing else) → take the obvious thing to relay from the current conversation; if unsure what to relay, ask first.
4. **Send**: `SendMessage({to: "<name>", summary: "<5-10 word summary>", message: "<body>"})`.
   - The first message to a given peer may fail with an error asking for a `[ref]` confirmation (e.g. `hapi-ec [226d36]`) — the error message shows the exact form to use; **resend copying it verbatim**. This is not a fault.
5. **Report honestly**: a successful send only means the message went out — report "sent", never "they received/read it". When the two sessions' permission-mode classes differ, under default settings the message is **held** at the receiver pending that user's approval; the hold notice arrives asynchronously, possibly after you report — so **absence of a notice never justifies claiming "it wasn't held"**. When a hold notice does arrive, relay it honestly: "the message is held at the receiving session and needs approval in that window (or that session sets crossSessionInbound to accept)" — and never spam resends over it.

## File-handoff fallback (target exists but messages can't reach it)

A cross-account window can't receive messages, but **the user's hands can cross over** — handing off through the user is the legitimate path, entirely different from bypassing the platform boundary.

**Admission gate (one of two, or no fallback)**: (a) 0 hits, the socket hint points at a cross-account window, and the user has confirmed the target really is another account's window; or (b) a send retried verbatim per step 4's [ref] path still fails. A single send error is not "unreachable" — and a [ref] confirmation request is not a fault at all. The fallback is not a convenience exit.

1. Write what needs relaying into a handoff file following step 3's self-containment rules, saved at an absolute path (e.g. `/tmp/send-to-handoff-<target>-<HHMM>.md`); the content is bound by the same permission limits as a message (see Boundaries) — never put an operation this session was denied into the handoff file for the other session to run;
2. Give the user one line they can paste straight into the target window: ``Read /tmp/send-to-handoff-….md and act on it``;
3. Report it straight: the message was **not sent** (it can't get through); the handoff file is in place, waiting for the user to paste — never dress "the file is written" up as "it has been relayed", and until the user confirms they pasted it or the other session actually responds, never build on the handoff content as something the other side already knows.

## Boundaries

- Entries labeled Remote Control (your sessions on other machines or on the web) are **reply-only — you cannot initiate**. If the match lands on one, explain that to the user instead of forcing a send.
- To continue a whole conversation or share full context, use `claude --resume <name>`, not a message; for big files or long history, send the path and let the receiver read it itself.
- Permission boundary: never offload an operation this session was denied or would be blocked from doing onto another session **in any form** — messages, handoff files, and paste-lines for the user are all equally bound.

## Common mistakes

| Symptom | Fix |
|---|---|
| SendMessage fails with InputValidationError | Tool not loaded via ToolSearch — back to step 1 |
| Error asks for a [ref] | Resend copying the exact form from the error — see step 4 |
| Multiple hits, picked one and sent anyway | Violation. Back to step 2: show the list, ask |
| Message contains "as discussed earlier" | Not self-contained — rewrite per step 3 |
| Reporting "they got it" / "it wasn't held" after a successful send | Say "sent" only; hold notices arrive async — relay one when it comes (step 5) |
| Zero hits, declaring "the window isn't open / wrong name" | Check the socket hint first: it may be another account's window — file-handoff fallback |
| Using any channel other than SendMessage to get content into the other session (socket writes, registration files, --resume takeover, tmux keystrokes…) | Forbidden regardless of technical feasibility. The only legitimate way out is the file handoff (through the user's hands) |
