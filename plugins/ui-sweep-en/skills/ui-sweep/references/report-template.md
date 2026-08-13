# UI Full Interaction Sweep Report (template)

- **Date**:
- **Driver**: agent-browser <version> (headless Chrome for Testing <version>) + ui-sweep traversal orchestrator
- **Target**: <site URL> (<login-state notes>, deployed version = <commit/pipeline>)
- **Method**: <N> screens (<screen id list>), an a11y snapshot builds the element plan for each screen, then per element "restore baseline → relocate → click → observe"; observation surface = page fingerprint change, uncaught exceptions, console error/warn, dialogs; destructive actions matched against the denylist are logged, never clicked; confirm/prompt dialogs are always dismissed (no real write is produced); <language/theme baseline lock notes>.

## Totals

**<N> ledger records (<N2> actual clicks). <M> page exceptions, <K> console errors.** Distribution: ok-changed <n1> / dead <n2> / dialog-dismissed <n3> / click-error <n4> / page-error <n5> / denylisted-unclicked (skipped-denylist) <n6> / miss-not-found <n7> / left-domain-recovered (left-domain) <n8>. (<n9> of these were relocated-by-index (note-relocated-by-index) — an annotation, not a separate category, already counted under the categories above.)

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
- <N> items left-domain-recovered (<list of element names>): the click navigated outside this pass's `ALLOWED_DOMAINS` and the engine forced a recovery on the spot, so this pass never actually verified that element's final state; if it's a legitimate in-product link to an upstream domain, add that domain to `ALLOWED_DOMAINS` and re-run to cover it.
