# SOP-<business-name>-runbook.md Template

> Used for degraded delivery when the target deployed URL is currently unreachable (needs Tailscale/an internal network).
> Once the network is back, follow this document to produce the real `docs/SOP-<business-name>.md`.

## Trigger conditions

- [ ] Tailscale/internal network is connected — `curl -I <deployed URL>` returns 200/3xx
- [ ] The test account is confirmed to work (don't record the username/password in this document)

## Skeleton already prepared (from project docs, no network needed)

### Roles and business steps

<!-- Distilled from HANDOVER.md / BUSINESS.md / REQUIREMENTS.md, format:
- Role A: Step 1 (which page?), Step 2 (which page?)
-->

### Page list to confirm

<!-- List pages/features guessable from the docs, tagged "pending traversal confirmation" -->

## Run once the network is back

```bash
# 1. Check whether playwright-mcp is already configured; prefer MCP if so
claude mcp list | grep -i playwright

# 2a. If MCP is configured: navigate/screenshot/take accessibility snapshots
#     directly with MCP tools in the conversation, following SKILL.md steps 2-5.

# 2b. If not configured, fall back to the native script. Credentials travel via
#     environment variables — don't write them into this file, and don't pass
#     them as --user/--pass command-line arguments (they'd land in shell history
#     and ps aux):
SOP_USER='<test account, entered live or read from .env>' \
SOP_PASS='<same>' \
node <this skill's base directory>/scripts/crawl.mjs \
  --url <deployed URL> \
  --out docs/sop-images

# 2c. For before/after pairs of key operations (form submissions, report exports, etc.),
#     optionally pass an action list:
node <this skill's base directory>/scripts/crawl.mjs \
  --url <deployed URL> --out docs/sop-images --actions <action-list.json>
```

## Self-check after producing the document (same as SKILL.md Step 5)

- [ ] Page matrix has full coverage
- [ ] Every feature has a screenshot; key operations have a before/after pair
- [ ] At least one real usage example
- [ ] No real credentials anywhere in the document
- [ ] Business jargon is explained the first time it appears
- [ ] UTF-8, no mangled characters
