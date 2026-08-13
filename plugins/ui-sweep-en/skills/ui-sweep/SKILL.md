---
name: ui-sweep
description: "Triggers before SOP screenshots to systematically click every interactive element on the site, as a regression sweep after a batch of UI changes, when the user says \"click through all the buttons\", or whenever an interaction smoke test is needed. Driven by agent-browser plus a generalized traversal engine: click and observe every element on every screen, log to a six-category ledger, and emit a JSONL ledger, a per-screen screenshot, and a report."
argument-hint: "[site URL] [login-state notes, optional]"
---

# ui-sweep — full UI interaction sweep

Before SOP screenshots, systematically click through the interface to catch the silent potholes — buttons that do nothing when clicked, buttons that throw errors — before you shoot the SOP or sign off a regression pass. Faster than eyeballing it by hand, and with deterministic coverage guarantees that random monkey testing doesn't give you. The driver is [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) (★40.5k, Apache-2.0, a Rust CLI built for AI agents: a11y snapshots with element references, click occlusion detection built in, `console`/`errors` capture, explicit confirm/prompt handling, `state save/load` for login-state injection, `--allowed-domains` domain locking), plus a self-built ~220-line traversal orchestrator (`scripts/sweep.mjs`). Verified in a real run against the stella project on 2026-08-13: 10 screens, 220 clicks, 0 page exceptions, 0 console errors, and it caught 1 real defect (a board "Add" action that silently did nothing on empty input).

## Requirements

- `npm i -g agent-browser` — bundles Chrome for Testing, no Playwright dependency (Apache-2.0). This skill was written against 0.27.0 (headless Chrome for Testing 152); behavior on other versions may differ.
- Node.js (to run `scripts/sweep.mjs` and `scripts/export-state.mjs`); `scripts/export-state.mjs` additionally depends on `playwright-core` (declared in `scripts/package.json`, one `npm i` covers it).

## The six-step flow

1. **Check dependencies**: confirm `agent-browser --version` runs; confirm the target is a site you own or are authorized to test (see the safety boundary below).
2. **Inject login state**: run `scripts/export-state.mjs --cdp <CDP address> --out <state.json> --origin <origin>...` to export cookies plus each origin's localStorage from an already-logged-in real browser (connected over CDP), producing a `{cookies, origins}` structure; then feed the sweep session the same login state with `agent-browser state load <state.json>`. **Never touch plaintext passwords** (the whole flow never types a password — it only relays state from an already-logged-in browser); **delete the login-state file the moment you're done with it, and never commit it to git**.
3. **Build the screen list** (the one part that needs per-project customization): first poke around manually, or `agent-browser open <ROOT>` + `snapshot -i`, to learn the structure of the first screen, then write each "screen" into the project's own `sweep.config.mjs`. A "screen" is a deterministic recovery path from `ROOT` (`{id, path: [{css}|{text}], settleMs?}` — `path` is the sequence of elements to click, in order, to reach that screen from the root). Every distinct state of an SPA's overlays/drawers/tabs counts as its own separate screen — don't skip any.
4. **Run the engine**: `node scripts/sweep.mjs <path>/sweep.config.mjs`. Run `--check-config` first to confirm the config is valid (missing `ROOT`/`SCREENS` fails fast instead of silently running an empty sweep); run the full sweep in default mode (without `--strict` — see the trade-off note below).
5. **Read the results**: the engine buckets every click into one of six categories — `ok-changed` (fingerprint changed, including checkbox checked state), `dead` (no reaction at all), `dialog-dismissed` (a dialog was dismissed), `click-error` (the click command itself errored), `page-error` (the page threw an uncaught exception), `skipped-denylist` (matched the denylist and was never clicked). **False-positive triage method** (distilled from the real run — apply these filters before deciding whether real-browser verification is needed):
   - For `click-error`, check the dialog ledger first — a synchronous `window.prompt`/`confirm` blocks the click command until it times out, and this kind of "error" is often the button working fine, just blocked by a synchronous dialog; if the ledger shows the prompt content and a dismissal record, that rules it out.
   - For `dead`, think "same-screen state accumulation" first: the engine doesn't restore the baseline after every single click by default (see the `--strict` note), so state left over from an earlier click on the same screen — an expanded panel, a hint already shown — can mask the effect of the current click and produce a false `dead`. Re-run the suspicious `dead` entries with `--strict` before drawing a conclusion.
   - Navigation buttons for the current state (already on that page) and header/page copies hidden behind an overlay legitimately show as `dead` — that's not a defect.
   - Under headless, browser APIs like fullscreen or native date pickers can be no-ops — that's an environment limitation, not a product bug.
   - A real defect (a `dead`/`click-error`/`page-error` judged to be an actual product problem) must be verified one by one in a real browser before it's called a defect — never conclude from the ledger alone.
6. **Produce the report**: follow the skeleton in `references/report-template.md` — five sections: totals, real defects (verified), false-positive triage (with the exclusion reasoning for each), observations (not indicted, but worth flagging), and coverage gaps (an honest accounting of what wasn't clicked and why).

## The `--strict` mode trade-off

Default (without `--strict`): within a screen, the baseline is restored only after a click that actually changed state; a run of consecutive "no reaction" clicks doesn't re-restore each time — this runs fast (roughly half the time of `--strict`), at the cost that same-screen state can accumulate and mask a later click's real effect, producing the `dead` false positives mentioned above.

`--strict`: unconditionally restores the baseline (re-runs `restore(screen)`) after every single click before moving to the next one — fixes the state-accumulation false positive, at the cost of running roughly 2x slower for a full sweep. **Recommendation**: run the first full-site pass in default mode, then re-run the suspicious entries in the `dead` list with `--strict` to verify them — you don't need to force `--strict` for the whole site.

## Safety boundary (hard rules)

- **Destructive buttons are logged, never clicked**: the engine has a built-in default denylist — revoke, dissolve, delete, log out / logout / sign out, archive, clear, reset, send, save, upload (each matched in both English and Chinese, as regexes). Matches are only logged to the ledger (`skipped-denylist`), never clicked. A project can **append** to the denylist via `DENY_EXTRA` (a regex) in `sweep.config.mjs`, but there is no configuration path that can trim or override the default denylist — the safety floor cannot be weakened by config.
- **`confirm`/`prompt` dialogs are always dismissed**: after every click the ledger checks dialog status, and any `confirm`/`prompt`/`alert` detected is unconditionally dismissed, so no real write is ever produced.
- **`--allowed-domains` locks the target domain**: the sweep only runs inside the target domain — the engine is never given the chance to wander outside it.
- **Only for sites you own or are authorized to test**: never run this skill against a third-party site without authorization.
- **Delete the login-state file when you're done with it**: the state file produced by `export-state.mjs` holds cookies/localStorage — treat it as a sensitive credential, delete it as soon as you're done, never commit it to git, never upload it.

## Known limitations (stated honestly)

- **Checkbox toggling is only verified at the fingerprint level**: the fingerprint includes a count of `input:checked`/`[aria-checked="true"]`, which catches the signal that "some checked state changed", but doesn't re-verify the semantics of any individual checkbox (what being checked actually means) — manual re-verification is still recommended for cases you're unsure about.
- **Some browser APIs are no-ops under headless**: fullscreen APIs, native date/color pickers, and similar can fail to produce real effects under headless Chrome — a `dead` result for these doesn't indicate a product defect.
- **Canvas/custom-drawn UI is out of scope**: a11y snapshots only see elements the accessibility tree perceives; interactions on a canvas or purely custom-drawn (non-standard-DOM) controls never show up in the traversal plan. This skill can't cover them — they need dedicated verification.

## Sources

- Real-run data: a run against the stella project on 2026-08-13, 10 screens, 220 clicks (ok-changed 106 / dead 97 / denylisted-unclicked 11 / click-error 2 / relocated-by-index 2 / miss-not-found 2), 0 page exceptions, 0 console errors, 1 real defect caught (a board "Add" action that silently did nothing on empty input).
- Driver: [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser), tested against 0.27.0 (headless Chrome for Testing 152).
- Research basis: internal tooling research (GitHub candidate comparison — agent-browser vs. playwright-mcp/chrome-devtools-mcp (MCP form; token/latency cost doesn't pencil out for a full sweep) vs. browser-use (non-deterministic) vs. crawlee (a URL crawler; the SPA in-screen state logic still has to be hand-written) vs. gremlins.js (random monkey testing, unmaintained)).
