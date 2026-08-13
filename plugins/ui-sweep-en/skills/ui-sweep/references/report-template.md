# UI Full Interaction Sweep Report (template)

- **Date**:
- **Driver**: agent-browser <version> (headless Chrome for Testing <version>) + ui-sweep traversal orchestrator
- **Target**: <site URL> (<login-state notes>, deployed version = <commit/pipeline>)
- **Method**: <N> screens (<screen id list>), an a11y snapshot builds the element plan for each screen, then per element "restore baseline → relocate → click → observe"; observation surface = page fingerprint change, uncaught exceptions, console error/warn, dialogs; destructive actions matched against the denylist are logged, never clicked; confirm/prompt dialogs are always dismissed (no real write is produced); <language/theme baseline lock notes>.

## Totals

**<N> clicks. <M> page exceptions, <K> console errors.** Distribution: ok-changed <n1> / dead <n2> / denylisted-unclicked <n3> / click-error <n4> / relocated-by-index <n5> / miss-not-found <n6>.

## Real defects (<count>, fixed/pending)

List each one — every entry must already be verified in a real browser before it's called a defect, never conclude from the ledger alone:

- **<one-line summary of the defect>**: <repro steps>. <verification evidence, e.g. "innerText N→N, zero error elements">. <fix status and commit/file>.

(If there are no real defects, write "No real defects found in this pass" — don't omit this section.)

## False-positive triage (each manually re-verified)

For ledger entries judged `dead`/`click-error`/`page-error` that turned out, on review, not to be product defects, state the exclusion reasoning for each (referencing the triage method in SKILL.md's "Read the results" step):

- <element/button name> judged <original category> ×<count>: <exclusion reasoning, e.g. "a synchronous prompt blocked the click command until timeout; the ledger shows the prompt content fired and was dismissed, the button itself works fine">.

## Observations (not indicted, kept as candidates)

Not enough to indict, but worth recording for later verification or product decisions:

- <one-line observation> — <why it's not indicted, suggested follow-up>.

## Coverage gaps (an honest accounting)

Parts this pass did not cover, and why (don't dress it up as "full coverage"):

- <N> items denylisted-unclicked (<list of button names>): destructive or would produce a real write, not clicked this pass.
- <miss-not-found / screens not built>: <reason>.
- <modules/upstream product UI out of scope>: <reason>.
