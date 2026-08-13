#!/usr/bin/env node
// ui-sweep 通用化遍历引擎 —— agent-browser 驱动
// 每屏:恢复现场 → snapshot -i 建元素计划 → 逐元素(恢复→定位→点击→观察→记账)
// 分类:ok-changed(状态变化)/dead(无任何反应)/dialog-dismissed(弹窗被驳回)/
//       click-error|page-error(异常)/skipped-denylist(拦截名单)/miss-not-found(定位失败)
//
// 用法:
//   node sweep.mjs <path>/sweep.config.mjs [--strict] [--check-config]
//
// config 必须用具名 export 提供(ESM):
//   export const ROOT = 'https://example.com/';      // 必填,起点 URL
//   export const SCREENS = [{ id, path: [...], settleMs? }, ...]; // 必填,屏清单
//   export const DENY_EXTRA = /.../i;                // 可选,叠加默认拦截名单(只增不减)
//   export async function ensureBaseline({ ab, evalJs, settle }) { ... } // 可选,项目基线钩子
//   export const OUT = './sweep-out';                // 可选,默认 ./sweep-out(相对 config 所在目录)
//
// --check-config:只做 config 校验(不导入 agent-browser、不联网、不跑真实站点),
//   校验通过打印 "config OK" 并 exit 0;缺 ROOT/SCREENS 时打印错误并 exit 1。
import { execFileSync } from 'node:child_process';
import { writeFileSync, appendFileSync, mkdirSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

// ---- 默认拦截名单(安全底线,config 只能通过 DENY_EXTRA 叠加,不可削减/覆盖) ----
const DENY_DEFAULT = /(吊销|解散|删除|退出|logout|sign ?out|revoke|归档|archive|清除|clear|重置|reset|发送|send|保存|save|上传|upload|^ask$)/i;

// ---- CLI 参数 ----
const argv = process.argv.slice(2);
const STRICT = argv.includes('--strict');
const CHECK_CONFIG_ONLY = argv.includes('--check-config');
const configPath = argv.find((a) => !a.startsWith('--'));

if (!configPath) {
  console.error('用法: node sweep.mjs <path>/sweep.config.mjs [--strict] [--check-config]');
  process.exit(1);
}

const configAbs = path.resolve(configPath);
const configDir = path.dirname(configAbs);

let config;
try {
  config = await import(pathToFileURL(configAbs).href);
} catch (e) {
  console.error(`config 加载失败: ${configAbs}\n${e.message}`);
  process.exit(1);
}

const { ROOT, SCREENS, DENY_EXTRA, ensureBaseline, OUT: OUT_CFG } = config;

// ---- 必填项校验:缺失立即报错退出,不静默空跑 ----
const configErrors = [];
if (!ROOT || typeof ROOT !== 'string') {
  configErrors.push('缺少必填项 ROOT(string,起点 URL)');
}
if (!Array.isArray(SCREENS) || SCREENS.length === 0) {
  configErrors.push('缺少必填项 SCREENS(非空数组,{id, path, settleMs?})');
}
if (DENY_EXTRA !== undefined && !(DENY_EXTRA instanceof RegExp)) {
  configErrors.push('DENY_EXTRA 若提供必须是 RegExp');
}
if (ensureBaseline !== undefined && typeof ensureBaseline !== 'function') {
  configErrors.push('ensureBaseline 若提供必须是 async function');
}
if (configErrors.length) {
  console.error(`sweep.config.mjs 校验失败(${configAbs}):`);
  for (const e of configErrors) console.error('  - ' + e);
  process.exit(1);
}

if (CHECK_CONFIG_ONLY) {
  console.log(`config OK: ROOT=${ROOT} SCREENS=${SCREENS.length} DENY_EXTRA=${DENY_EXTRA ? 'yes' : 'no'} ensureBaseline=${ensureBaseline ? 'yes' : 'no'}`);
  process.exit(0);
}

// ---- 输出目录(默认 ./sweep-out,相对 config 所在目录) ----
const OUT = path.resolve(configDir, OUT_CFG || './sweep-out') + path.sep;
mkdirSync(OUT, { recursive: true });
const LEDGER = OUT + 'ledger.jsonl';
writeFileSync(LEDGER, '');

function isDenied(name) {
  if (DENY_DEFAULT.test(name)) return true;
  if (DENY_EXTRA instanceof RegExp && DENY_EXTRA.test(name)) return true;
  return false;
}

function ab(args, { json = false, ok = false } = {}) {
  try {
    const out = execFileSync('agent-browser', json ? [...args, '--json'] : args, { encoding: 'utf8', timeout: 45000 });
    return json ? JSON.parse(out) : out;
  } catch (e) {
    if (ok) return null;
    return { __err: (e.stdout || '') + (e.stderr || e.message) };
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function settle(ms = 1200) {
  ab(['wait', '--load', 'networkidle', '--timeout', '8000'], { ok: true });
  await sleep(ms);
}

// 任意 JS 求值(暴露给 ensureBaseline 钩子)
function evalJs(js) {
  return ab(['eval', js]);
}

// 文本精确点击(前台小卡这类无稳定选择器的目标)
function evalClickText(text) {
  const js = `(() => { const cs=[...document.querySelectorAll('*')].filter(e=>(e.textContent||'').trim()===${JSON.stringify(text)}&&e.children.length===0&&e.getBoundingClientRect().width>0); const c=cs[cs.length-1]; if(c){c.click();return true;} return false; })()`;
  const r = ab(['eval', js]);
  return String(r).includes('true');
}

function clickTopCss(sel) {
  const js = `(() => { const cs=[...document.querySelectorAll(${JSON.stringify(sel)})].filter(e=>{const r=e.getBoundingClientRect(); if(r.width===0)return false; const h=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2); return h&&(h===e||e.contains(h)||h.contains(e));}); const el=cs[cs.length-1]; if(el){el.click();return true;} return false; })()`;
  return String(ab(['eval', js])).includes('true');
}

async function restore(screen) {
  ab(['open', ROOT]);
  await settle(2000);
  // 项目相关的基线钩子(如 stella 的语言锁):由 config 的 ensureBaseline 提供,引擎本身不内置任何项目专属逻辑
  if (typeof ensureBaseline === 'function') {
    await ensureBaseline({ ab, evalJs, settle });
  }
  for (const op of screen.path) {
    let ok = false;
    if (op.css) ok = clickTopCss(op.css);
    else if (op.text) ok = evalClickText(op.text);
    if (!ok) return false;
    await settle(1200);
  }
  await settle(screen.settleMs || 1500);
  return true;
}

function fingerprint() {
  // url + 元素数 + 正文文本长 + 勾选态计数(checkbox/aria-checked)
  const r = ab(['eval', `location.href + '|' + document.querySelectorAll('*').length + '|' + document.body.innerText.length + '|' + document.querySelectorAll('input:checked,[aria-checked="true"]').length`]);
  return String(r).trim();
}

function snapshotPlan() {
  const raw = String(ab(['snapshot', '-i']));
  const els = [];
  for (const line of raw.split('\n')) {
    const m = /^\s*-\s+(\w+)\s+"([^"]*)"\s+\[.*ref=(e\d+)/.exec(line);
    if (m) els.push({ role: m[1], name: m[2], ref: m[3] });
  }
  return els;
}

function grabErrors() {
  const errs = String(ab(['errors'])).trim();
  const cons = String(ab(['console'])).trim();
  const consErr = cons.split('\n').filter((l) => /\[(error|warn)\]/i.test(l));
  ab(['errors', '--clear'], { ok: true });
  ab(['console', '--clear'], { ok: true });
  return { pageErrors: errs && !/no errors/i.test(errs) ? errs.slice(0, 500) : '', consoleIssues: consErr.slice(0, 5).join(' || ').slice(0, 500) };
}

function log(rec) { appendFileSync(LEDGER, JSON.stringify(rec) + '\n'); }

const CLICK_ROLES = new Set(['button', 'link', 'tab', 'menuitem', 'checkbox', 'radio', 'combobox', 'switch']);

for (const screen of SCREENS) {
  console.log('=== SCREEN', screen.id);
  if (!(await restore(screen))) { log({ screen: screen.id, result: 'screen-restore-failed' }); console.log('RESTORE FAIL'); continue; }
  ab(['screenshot', OUT + screen.id + '.png'], { ok: true });
  grabErrors(); // 清掉加载期噪音,单独记屏级
  const plan = snapshotPlan().filter((e) => CLICK_ROLES.has(e.role));
  console.log('elements:', plan.length);
  log({ screen: screen.id, result: 'screen-plan', count: plan.length, names: plan.map((p) => p.name).slice(0, 60) });

  let dirty = false; // 上一个点击是否改变了状态(需要恢复);--strict 下无条件每击恢复
  for (let k = 0; k < plan.length; k++) {
    const want = plan[k];
    if (isDenied(want.name)) { log({ screen: screen.id, k, name: want.name, role: want.role, result: 'skipped-denylist' }); continue; }
    if (STRICT || dirty) { if (!(await restore(screen))) { log({ screen: screen.id, k, result: 'restore-failed' }); break; } dirty = false; }
    // 重新快照定位(refs 每次会变):按 role+name 找,重名取第 n 个
    const now = snapshotPlan();
    const dupIdx = plan.slice(0, k).filter((p) => p.role === want.role && p.name === want.name).length;
    const matches = now.filter((p) => p.role === want.role && p.name === want.name);
    let target = matches[dupIdx] || matches[0];
    if (!target) {
      // 名字对不上(语言/主题切换把名字改了):回落到「同角色序列里的同位置」
      const nowClickable = now.filter((e) => CLICK_ROLES.has(e.role));
      target = nowClickable[k];
      if (target) log({ screen: screen.id, k, name: want.name, role: want.role, result: 'note-relocated-by-index', foundName: target.name });
    }
    if (!target) { log({ screen: screen.id, k, name: want.name, role: want.role, result: 'miss-not-found' }); continue; }
    const before = fingerprint();
    const clickRes = ab(['click', '@' + target.ref]);
    const clickErr = clickRes && clickRes.__err ? String(clickRes.__err).slice(0, 200) : '';
    await sleep(900);
    // 弹窗?一律驳回
    const dlg = String(ab(['dialog', 'status'], { ok: true }) || '');
    let dialog = '';
    if (/open|pending|confirm|prompt|alert/i.test(dlg) && !/no dialog/i.test(dlg)) {
      dialog = dlg.replace(/\n/g, ' ').slice(0, 120);
      ab(['dialog', 'dismiss'], { ok: true });
      await sleep(400);
    }
    const { pageErrors, consoleIssues } = grabErrors();
    const after = fingerprint();
    const changed = before !== after;
    dirty = changed || !!dialog;
    let result = 'dead';
    if (clickErr) result = 'click-error';
    else if (pageErrors) result = 'page-error';
    else if (dialog) result = 'dialog-dismissed';
    else if (changed) result = 'ok-changed';
    log({ screen: screen.id, k, name: want.name, role: want.role, result, clickErr, dialog, pageErrors, consoleIssues, urlAfter: after.split('|')[0] });
    console.log(`  [${k}] ${want.role} "${want.name}" -> ${result}`);
  }
}

console.log('SWEEP DONE, ledger:', LEDGER);
