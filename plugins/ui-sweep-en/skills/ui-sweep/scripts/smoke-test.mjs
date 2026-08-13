#!/usr/bin/env node
// sweep.mjs 的 config 解析冒烟测试 —— 不依赖 agent-browser,不联网,不跑真实站点。
// 全部走 `node sweep.mjs <config> [--check-config|--check-deny <name>...|--check-domain <url>...]`,
// 只验证 config 校验分支、isDenied() 纯函数分支与 isLeftDomain() 纯函数分支,不碰 agent-browser。
//
// 用例:
//   1) 缺 ROOT           → 非 0 退出,stderr 含 "ROOT"
//   2) 缺 SCREENS         → 非 0 退出,stderr 含 "SCREENS"
//   3) 合法 config 可加载 → exit 0,stdout 含 "config OK"
//   4) DENY_EXTRA 带 /g 标志时,用 --check-deny 连续判定同一名字 4 次
//      → 4 次全部 denied:true(回归 RegExp.test() 在 /g 标志下推进 lastIndex、
//      导致同名破坏性按钮隔一个漏一个被真点的 bug)
//   5) DENY_EXTRA 带 /y(sticky)标志、及 /gy 组合标志时,同样连续判定 4 次
//      → 4 次全部 denied:true(/y 与 /g 一样会推进 lastIndex,同一处回归)
//   6) --check-domain:ALLOWED_DOMAINS 内的 URL → left-domain:false;
//      ALLOWED_DOMAINS 外的 URL(点击跳转逃逸场景)→ left-domain:true
//      (--allowed-domains 只挡显式导航、挡不住点击跳转——0.27.0 实测,
//      引擎侧逐击域名校验是可靠层,见 SKILL.md 安全边界)
//   7) 孤儿功能对账(orphan-audit,spec 2026-08-13):
//      - URL 归一化(--check-normalize-api / --check-normalize-route):数字段/UUID 段/
//        长 hex 段均替换为 :id(`/projects/123` → `/projects/:id` 等三种);尾斜杠归一化
//        (非根路径去掉末尾 '/',根路径保留,回归 Astro/Next 尾斜杠假阳性)
//      - 差集纯函数(--check-orphan-diff):unreachable 排除 exempt 命中项、broken-entry
//        取 status>=400(含未在 INVENTORY 里的)、exempt_hits 计数
//      - config 校验:INVENTORY.apis/routes/exempt 类型不符时非 0 退出
//      - network requests JSON 形状解析(--check-parse-network):喂一段
//        agent-browser 0.x 实测的真实响应形状 {"success":true,"data":{"requests":[...]}}
//        (回归"按裸数组解析导致 seenApis 恒为空、对账功能整条静默死掉"的 bug)
//   8) 终审打回修复(2026-08-13 第二轮):
//      - F6:破坏性拦截名单补英文词(delete/remove/dissolve/discard/drop)——回归"英文 UI 的
//        <button>Delete item</button> 被真点、POST 真发出"(旧正则只有中文「删除」)
//      - F3:coverage_note 采集失灵不可辨(--check-coverage-note)——网络采集解析失败次数>0、
//        或整轮采集次数为 0 时,coverage_note 必须带警告文字,且绝不能输出"full coverage"
//        强断言(哪怕 coverageGaps 是空的)
import { spawnSync } from 'node:child_process';
import { writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SWEEP = path.join(HERE, 'sweep.mjs');

let pass = 0, fail = 0;
function ok(name) { pass++; console.log(`PASS: ${name}`); }
function bad(name, detail) { fail++; console.log(`FAIL: ${name}${detail ? ' — ' + detail : ''}`); }

function run(args) {
  // spawnSync (not execFileSync) so stderr is captured on BOTH success and failure exit codes —
  // execFileSync only hands back e.stderr when the process throws (non-zero exit), so a warning
  // printed to stderr by an exit-0 run (e.g. the network-shape parse warning) would silently go
  // to the test runner's own stderr instead of being visible to assertions here.
  const r = spawnSync('node', [SWEEP, ...args], { encoding: 'utf8' });
  return { code: r.status ?? 1, stdout: r.stdout || '', stderr: r.stderr || '' };
}

const tmp = mkdtempSync(path.join(os.tmpdir(), 'ui-sweep-smoke-'));

try {
  // Case 1: missing ROOT
  const noRoot = path.join(tmp, 'no-root.config.mjs');
  writeFileSync(noRoot, `export const SCREENS = [{ id: 'home', path: [] }];\n`);
  {
    const r = run([noRoot, '--check-config']);
    if (r.code !== 0 && /ROOT/.test(r.stderr)) ok('missing ROOT exits with an error');
    else bad('missing ROOT exits with an error', `code=${r.code} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 2: missing SCREENS
  const noScreens = path.join(tmp, 'no-screens.config.mjs');
  writeFileSync(noScreens, `export const ROOT = 'https://example.com/';\n`);
  {
    const r = run([noScreens, '--check-config']);
    if (r.code !== 0 && /SCREENS/.test(r.stderr)) ok('missing SCREENS exits with an error');
    else bad('missing SCREENS exits with an error', `code=${r.code} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 3: a valid config loads
  const valid = path.join(tmp, 'valid.config.mjs');
  writeFileSync(valid, `export const ROOT = 'https://example.com/';\nexport const SCREENS = [{ id: 'home', path: [] }];\n`);
  {
    const r = run([valid, '--check-config']);
    if (r.code === 0 && /config OK/.test(r.stdout)) ok('a valid config loads (--check-config)');
    else bad('a valid config loads (--check-config)', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 4: DENY_EXTRA with a /g flag must not miss alternating matches (lastIndex regression)
  const gFlag = path.join(tmp, 'g-flag.config.mjs');
  writeFileSync(gFlag, `export const ROOT = 'https://example.com/';\nexport const SCREENS = [{ id: 'home', path: [] }];\nexport const DENY_EXTRA = /^danger-button$/gi;\n`);
  {
    const r = run([gFlag, '--check-deny', 'danger-button', '--check-deny', 'danger-button', '--check-deny', 'danger-button', '--check-deny', 'danger-button']);
    let allDenied = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      allDenied = Array.isArray(parsed) && parsed.length === 4 && parsed.every((x) => x.denied === true);
    } catch { /* leave allDenied = false, reported below */ }
    if (r.code === 0 && allDenied) ok('DENY_EXTRA with a /g flag denies the same name on all 4 consecutive checks');
    else bad('DENY_EXTRA with a /g flag denies the same name on all 4 consecutive checks', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 5: DENY_EXTRA with /y and /gy flags must not miss alternating matches either
  //         (RegExp.test() advances lastIndex under the sticky flag the same way it
  //         does under /g; both must be stripped, not just /g)
  for (const [label, flags] of [['/y', 'y'], ['/gy', 'gy']]) {
    const cfgPath = path.join(tmp, `${flags}-flag.config.mjs`);
    writeFileSync(cfgPath, `export const ROOT = 'https://example.com/';\nexport const SCREENS = [{ id: 'home', path: [] }];\nexport const DENY_EXTRA = /^danger-button$/${flags}i;\n`);
    const r = run([cfgPath, '--check-deny', 'danger-button', '--check-deny', 'danger-button', '--check-deny', 'danger-button', '--check-deny', 'danger-button']);
    let allDenied = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      allDenied = Array.isArray(parsed) && parsed.length === 4 && parsed.every((x) => x.denied === true);
    } catch { /* leave allDenied = false, reported below */ }
    if (r.code === 0 && allDenied) ok(`DENY_EXTRA with a ${label} flag denies the same name on all 4 consecutive checks`);
    else bad(`DENY_EXTRA with a ${label} flag denies the same name on all 4 consecutive checks`, `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 6: --check-domain — the reliable-layer per-click domain guard (pure function,
  // no agent-browser). ALLOWED_DOMAINS derives from ROOT's hostname when not set explicitly.
  const domainCfg = path.join(tmp, 'domain.config.mjs');
  writeFileSync(domainCfg, `export const ROOT = 'http://localhost:8898/';\nexport const SCREENS = [{ id: 'home', path: [] }];\n`);
  {
    const r = run([domainCfg, '--check-domain', 'http://localhost:8898/some/page', '--check-domain', 'http://127.0.0.1:8899/']);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = Array.isArray(parsed) && parsed.length === 2
        && parsed[0].leftDomain === false
        && parsed[1].leftDomain === true;
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('--check-domain classifies an in-allowlist URL as leftDomain:false and an out-of-allowlist URL as leftDomain:true');
    else bad('--check-domain classifies an in-allowlist URL as leftDomain:false and an out-of-allowlist URL as leftDomain:true', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 7a: URL normalization — numeric / UUID / long-hex segments all fold to :id
  {
    const r = run([
      valid,
      '--check-normalize-api', 'GET', 'https://example.com/projects/123',
      '--check-normalize-api', 'get', 'https://example.com/users/550e8400-e29b-41d4-a716-446655440000/profile',
      '--check-normalize-api', 'POST', '/items/deadbeef01?x=1#frag',
    ]);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = Array.isArray(parsed) && parsed.length === 3
        && parsed[0].normalized === 'GET /projects/:id'
        && parsed[1].normalized === 'GET /users/:id/profile'
        && parsed[2].normalized === 'POST /items/:id';
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('normalizeApi folds numeric/UUID/long-hex segments to :id');
    else bad('normalizeApi folds numeric/UUID/long-hex segments to :id', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 7b: route normalization strips query/hash and folds id segments too
  {
    const r = run([valid, '--check-normalize-route', 'https://example.com/projects/42/edit?tab=info']);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = Array.isArray(parsed) && parsed.length === 1 && parsed[0].normalized === '/projects/:id/edit';
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('normalizeRoute folds id segments and strips query string');
    else bad('normalizeRoute folds id segments and strips query string', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 7c: route normalization strips a trailing slash on non-root paths but keeps the root
  // ('/' must stay '/', not collapse to '') — Astro/Next-style sites that default to trailing
  // slashes would otherwise false-positive their entire route inventory as unreachable.
  {
    const r = run([
      valid,
      '--check-normalize-route', 'http://example.com/dashboard/',
      '--check-normalize-route', 'http://example.com/',
    ]);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = Array.isArray(parsed) && parsed.length === 2
        && parsed[0].normalized === '/dashboard'
        && parsed[1].normalized === '/';
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('normalizeRoute strips a trailing slash on non-root paths and keeps the root as /');
    else bad('normalizeRoute strips a trailing slash on non-root paths and keeps the root as /', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 8: diffOrphans pure function — exempt filtering + broken-entry (incl. entries not in INVENTORY)
  const inventoryCfg = path.join(tmp, 'inventory.config.mjs');
  writeFileSync(inventoryCfg, [
    `export const ROOT = 'https://example.com/';`,
    `export const SCREENS = [{ id: 'home', path: [] }];`,
    `export const INVENTORY = {`,
    `  apis: ['GET /api/projects', 'POST /api/webhooks/stripe', 'GET /api/reports'],`,
    `  routes: ['/dashboard', '/admin'],`,
    `  exempt: [/^POST \\/api\\/webhooks/],`,
    `};`,
  ].join('\n'));
  {
    const seenPayload = JSON.stringify({
      seenApis: { 'GET /api/projects': 200, 'GET /api/legacy': 500 },
      seenRoutes: ['/dashboard'],
    });
    const r = run([inventoryCfg, '--check-orphan-diff', seenPayload]);
    let good = false;
    let parsed;
    try {
      parsed = JSON.parse(r.stdout.trim());
      const unreachableOk = Array.isArray(parsed.unreachable)
        && parsed.unreachable.includes('GET /api/reports')
        && parsed.unreachable.includes('/admin')
        && !parsed.unreachable.includes('POST /api/webhooks/stripe')
        && !parsed.unreachable.includes('GET /api/projects')
        && !parsed.unreachable.includes('/dashboard');
      const brokenOk = Array.isArray(parsed.broken)
        && parsed.broken.some((b) => b.key === 'GET /api/legacy' && Number(b.status) === 500);
      const exemptOk = Array.isArray(parsed.exemptHits) && parsed.exemptHits.includes('POST /api/webhooks/stripe');
      good = unreachableOk && brokenOk && exemptOk;
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('diffOrphans excludes exempt hits from unreachable and reports broken entries beyond INVENTORY');
    else bad('diffOrphans excludes exempt hits from unreachable and reports broken entries beyond INVENTORY', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 9: INVENTORY config validation — type mismatches exit non-zero
  const badInventoryApis = path.join(tmp, 'bad-inventory-apis.config.mjs');
  writeFileSync(badInventoryApis, [
    `export const ROOT = 'https://example.com/';`,
    `export const SCREENS = [{ id: 'home', path: [] }];`,
    `export const INVENTORY = { apis: 'GET /api/projects' };`,
  ].join('\n'));
  {
    const r = run([badInventoryApis, '--check-config']);
    if (r.code !== 0 && /INVENTORY\.apis/.test(r.stderr)) ok('INVENTORY.apis wrong type exits with an error');
    else bad('INVENTORY.apis wrong type exits with an error', `code=${r.code} stderr=${JSON.stringify(r.stderr)}`);
  }

  const badInventoryExempt = path.join(tmp, 'bad-inventory-exempt.config.mjs');
  writeFileSync(badInventoryExempt, [
    `export const ROOT = 'https://example.com/';`,
    `export const SCREENS = [{ id: 'home', path: [] }];`,
    `export const INVENTORY = { exempt: ['/not-a-regexp/'] };`,
  ].join('\n'));
  {
    const r = run([badInventoryExempt, '--check-config']);
    if (r.code !== 0 && /INVENTORY\.exempt/.test(r.stderr)) ok('INVENTORY.exempt wrong type exits with an error');
    else bad('INVENTORY.exempt wrong type exits with an error', `code=${r.code} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 10: valid INVENTORY loads fine via --check-config
  {
    const r = run([inventoryCfg, '--check-config']);
    if (r.code === 0 && /INVENTORY=yes/.test(r.stdout)) ok('a valid INVENTORY config loads (--check-config)');
    else bad('a valid INVENTORY config loads (--check-config)', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 10b: --check-config output for a config WITHOUT INVENTORY must be byte-identical to the
  // pre-orphan-audit format (acceptance criterion 1: "unconfigured INVENTORY behaves exactly like
  // before, zero side effects" — this covers --check-config's own stdout, not just runtime behavior).
  {
    const r = run([valid, '--check-config']);
    const expected = `config OK: ROOT=https://example.com/ SCREENS=1 DENY_EXTRA=no ALLOWED_DOMAINS=example.com STATE_FILE=no ensureBaseline=no\n`;
    if (r.code === 0 && r.stdout === expected) ok('--check-config output is byte-identical to the pre-orphan-audit format when INVENTORY is not configured');
    else bad('--check-config output is byte-identical to the pre-orphan-audit format when INVENTORY is not configured', `stdout=${JSON.stringify(r.stdout)} expected=${JSON.stringify(expected)}`);
  }

  // Case 11a: --check-parse-network against the REAL agent-browser 0.x response shape —
  // {"success":true,"data":{"requests":[...]},"error":null} — not a bare array. This is the
  // regression test for "the collector parsed the wrong JSON shape and the whole audit feature
  // died silently" (Array.isArray() on the wrapper object is always false).
  {
    const realShapePayload = JSON.stringify({
      success: true,
      data: { requests: [{ method: 'GET', url: 'https://example.com/api/projects/123?x=1', status: 404 }] },
      error: null,
    });
    const r = run([valid, '--check-parse-network', realShapePayload]);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = parsed['GET /api/projects/:id'] === 404;
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('extractNetworkRequests parses the real agent-browser {data:{requests:[...]}} shape into seenApis');
    else bad('extractNetworkRequests parses the real agent-browser {data:{requests:[...]}} shape into seenApis', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 11b: --check-parse-network still accepts a bare array (forward/backward compatibility
  // with a different agent-browser version that returns the requests array directly).
  {
    const bareArrayPayload = JSON.stringify([{ method: 'POST', url: '/api/projects/42/archive', status: 200 }]);
    const r = run([valid, '--check-parse-network', bareArrayPayload]);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = parsed['POST /api/projects/:id/archive'] === 200;
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('extractNetworkRequests still accepts a bare requests array');
    else bad('extractNetworkRequests still accepts a bare requests array', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 11c: an unparseable shape yields an empty result (no crash) AND prints a warning once,
  // so a future shape change doesn't get swallowed silently the way this one did.
  {
    const unparseablePayload = JSON.stringify({ unexpected: 'shape' });
    const r = run([valid, '--check-parse-network', unparseablePayload]);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = parsed && typeof parsed === 'object' && Object.keys(parsed).length === 0;
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good && /warning/i.test(r.stderr)) ok('extractNetworkRequests returns empty and warns once on an unparseable shape');
    else bad('extractNetworkRequests returns empty and warns once on an unparseable shape', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 11d: third review round (G1) — F5 only stopped out-of-domain URLs from polluting
  // seenRoutes; collectNetworkRequests() had no equivalent guard, so out-of-domain/third-party
  // XHR (analytics beacons, Sentry, Stripe, Intercom, CDN health-pings — every real site has
  // some) got written into seenApis by pathname only, colliding with a same-pathname in-domain
  // entry. `valid` config's ROOT is https://example.com/, so ALLOWED_DOMAINS derives to
  // example.com; a request to a different host with the SAME pathname as an in-domain orphan
  // must not appear in the parsed seenApis at all — same-key collision would silently erase a
  // real orphan (unreachable false negative) and could forge its status into broken-entry.
  {
    const mixedDomainPayload = JSON.stringify({
      success: true,
      data: {
        requests: [
          { method: 'GET', url: 'https://example.com/api/orders/7', status: 200 },
          { method: 'GET', url: 'https://thirdparty-analytics.example.net/api/orders/7', status: 404 },
          { method: 'POST', url: 'https://cdn.stripe.com/track', status: 200 },
        ],
      },
      error: null,
    });
    const r = run([valid, '--check-parse-network', mixedDomainPayload]);
    let good = false;
    let parsed;
    try {
      parsed = JSON.parse(r.stdout.trim());
      good = parsed['GET /api/orders/:id'] === 200
        && !('POST /track' in parsed)
        && Object.keys(parsed).length === 1;
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('accumulateSeenApis drops out-of-domain/third-party requests instead of letting their pathname collide with an in-domain entry');
    else bad('accumulateSeenApis drops out-of-domain/third-party requests instead of letting their pathname collide with an in-domain entry', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 12: F6 — the default denylist must catch destructive English words AND their Chinese
  // equivalents. Regression for a real English-UI <button>Delete item</button> that got clicked
  // for real (POST actually fired) because an earlier regex only had 删除, not "delete". Third
  // review round (G2): the previous version of this case only ever asserted the English half —
  // 23 smoke cases and not one exercised the Chinese half of DENY_DEFAULT, which is exactly the
  // kind of "guard only guards half the languages, nobody notices" gap that caused F6 in the
  // first place. Both halves are asserted together now so this case can't silently regress to
  // English-only coverage again.
  {
    const destructiveNames = [
      'Delete item', 'Remove group', 'Dissolve team', 'Discard draft', 'Drop table',
      '删除条目', '吊销令牌',
    ];
    const r = run([valid, ...destructiveNames.flatMap((n) => ['--check-deny', n])]);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = Array.isArray(parsed) && parsed.length === destructiveNames.length && parsed.every((x) => x.denied === true);
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('default denylist catches destructive words in both English (delete/remove/dissolve/discard/drop) and Chinese (删除/吊销), not just one language');
    else bad('default denylist catches destructive words in both English (delete/remove/dissolve/discard/drop) and Chinese (删除/吊销), not just one language', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 13a: F3 — a config with no parse failures and at least one collection attempt gets the
  // unqualified "full coverage" note (the pre-existing happy path must still work).
  {
    const r = run([valid, '--check-coverage-note', JSON.stringify({ coverageGaps: [], networkParseFailureCount: 0, networkCollectionAttempts: 5 })]);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = /^full coverage/.test(parsed.coverage_note);
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('buildCoverageNote reports full coverage when there are no gaps, no parse failures, and collection ran');
    else bad('buildCoverageNote reports full coverage when there are no gaps, no parse failures, and collection ran', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 13b: F3 — network parse failures must produce a warning in coverage_note and must NEVER
  // let "full coverage" be asserted, even though coverageGaps is empty (every screen restored
  // fine — the failure is in parsing the network log, not in navigation).
  {
    const r = run([valid, '--check-coverage-note', JSON.stringify({ coverageGaps: [], networkParseFailureCount: 3, networkCollectionAttempts: 5 })]);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = /network collection failed/i.test(parsed.coverage_note) && /3/.test(parsed.coverage_note) && !/^full coverage/.test(parsed.coverage_note);
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('buildCoverageNote warns and never claims full coverage when network parsing failed N times');
    else bad('buildCoverageNote warns and never claims full coverage when network parsing failed N times', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 13c: F3 — zero collection attempts across the whole run (network collection never ran
  // at all) must also be flagged and must never claim full coverage, even with zero gaps.
  {
    const r = run([valid, '--check-coverage-note', JSON.stringify({ coverageGaps: [], networkParseFailureCount: 0, networkCollectionAttempts: 0 })]);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = /network collection never ran/i.test(parsed.coverage_note) && !/^full coverage/.test(parsed.coverage_note);
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('buildCoverageNote warns and never claims full coverage when collection attempted 0 times');
    else bad('buildCoverageNote warns and never claims full coverage when collection attempted 0 times', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }

  // Case 13d: F3 — coverage gaps and network parse failures both present get combined into one
  // note, not silently dropping either signal.
  {
    const r = run([valid, '--check-coverage-note', JSON.stringify({ coverageGaps: ['home'], networkParseFailureCount: 2, networkCollectionAttempts: 5 })]);
    let good = false;
    try {
      const parsed = JSON.parse(r.stdout.trim());
      good = /incomplete coverage on screen\(s\): home/.test(parsed.coverage_note) && /network collection failed/i.test(parsed.coverage_note);
    } catch { /* leave good = false, reported below */ }
    if (r.code === 0 && good) ok('buildCoverageNote combines screen coverage gaps and network parse failures into one note');
    else bad('buildCoverageNote combines screen coverage gaps and network parse failures into one note', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
