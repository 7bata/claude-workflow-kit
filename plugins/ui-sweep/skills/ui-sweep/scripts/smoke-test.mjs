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
import { execFileSync } from 'node:child_process';
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
  try {
    const stdout = execFileSync('node', [SWEEP, ...args], { encoding: 'utf8' });
    return { code: 0, stdout, stderr: '' };
  } catch (e) {
    return { code: e.status ?? 1, stdout: e.stdout || '', stderr: e.stderr || '' };
  }
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
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
