#!/usr/bin/env node
// sweep.mjs 的 config 解析冒烟测试 —— 不依赖 agent-browser,不联网,不跑真实站点。
// 全部走 `node sweep.mjs <config> --check-config`,只验证 config 校验分支。
//
// 用例:
//   1) 缺 ROOT           → 非 0 退出,stderr 含 "ROOT"
//   2) 缺 SCREENS         → 非 0 退出,stderr 含 "SCREENS"
//   3) 合法 config 可加载 → exit 0,stdout 含 "config OK"
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

function run(configPath) {
  try {
    const stdout = execFileSync('node', [SWEEP, configPath, '--check-config'], { encoding: 'utf8' });
    return { code: 0, stdout, stderr: '' };
  } catch (e) {
    return { code: e.status ?? 1, stdout: e.stdout || '', stderr: e.stderr || '' };
  }
}

const tmp = mkdtempSync(path.join(os.tmpdir(), 'ui-sweep-smoke-'));

try {
  // 用例 1:缺 ROOT
  const noRoot = path.join(tmp, 'no-root.config.mjs');
  writeFileSync(noRoot, `export const SCREENS = [{ id: 'home', path: [] }];\n`);
  {
    const r = run(noRoot);
    if (r.code !== 0 && /ROOT/.test(r.stderr)) ok('缺 ROOT 报错退出');
    else bad('缺 ROOT 报错退出', `code=${r.code} stderr=${JSON.stringify(r.stderr)}`);
  }

  // 用例 2:缺 SCREENS
  const noScreens = path.join(tmp, 'no-screens.config.mjs');
  writeFileSync(noScreens, `export const ROOT = 'https://example.com/';\n`);
  {
    const r = run(noScreens);
    if (r.code !== 0 && /SCREENS/.test(r.stderr)) ok('缺 SCREENS 报错退出');
    else bad('缺 SCREENS 报错退出', `code=${r.code} stderr=${JSON.stringify(r.stderr)}`);
  }

  // 用例 3:合法 config 可加载
  const valid = path.join(tmp, 'valid.config.mjs');
  writeFileSync(valid, `export const ROOT = 'https://example.com/';\nexport const SCREENS = [{ id: 'home', path: [] }];\n`);
  {
    const r = run(valid);
    if (r.code === 0 && /config OK/.test(r.stdout)) ok('合法 config 可加载(--check-config)');
    else bad('合法 config 可加载(--check-config)', `code=${r.code} stdout=${JSON.stringify(r.stdout)} stderr=${JSON.stringify(r.stderr)}`);
  }
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
