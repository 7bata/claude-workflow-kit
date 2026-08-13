#!/usr/bin/env node
// ui-sweep 通用化遍历引擎 —— agent-browser 驱动
// 每屏:恢复现场 → snapshot -i 建元素计划 → 逐元素(恢复→定位→点击→观察→记账)
// 分类:ok-changed(状态变化)/dead(无任何反应)/dialog-dismissed(弹窗被驳回)/
//       click-error|page-error(异常)/skipped-denylist(拦截名单)/miss-not-found(定位失败)/
//       left-domain(点击后跑出 ALLOWED_DOMAINS,已强制拉回——见下方「域名边界」)
//
// 用法:
//   node sweep.mjs <path>/sweep.config.mjs [--strict] [--check-config]
//
// config 必须用具名 export 提供(ESM):
//   export const ROOT = 'https://example.com/';      // 必填,起点 URL
//   export const SCREENS = [{ id, path: [...], settleMs? }, ...]; // 必填,屏清单
//   export const DENY_EXTRA = /.../i;                // 可选,叠加默认拦截名单(只增不减)
//   export const ALLOWED_DOMAINS = 'example.com';    // 可选,逗号分隔域名/pattern,原样传给
//                                                     // agent-browser --allowed-domains;
//                                                     // 缺省时从 ROOT 的 hostname 推导
//   export const STATE_FILE = '/path/state.json';    // 可选,登录态文件;引擎在受限会话建立
//                                                     // 后自行 `state load`(不再要求用户手动预载)
//   export async function ensureBaseline({ ab, evalJs, settle }) { ... } // 可选,项目基线钩子
//   export const OUT = './sweep-out';                // 可选,默认 ./sweep-out(相对 config 所在目录)
//
// --check-config:只做 config 校验(不导入 agent-browser、不联网、不跑真实站点),
//   校验通过打印 "config OK" 并 exit 0;缺 ROOT/SCREENS 时打印错误并 exit 1。
//
// --check-deny <name>(可重复传):纯 isDenied() 校验钩子,不碰 agent-browser、不建 OUT 目录,
//   用于冒烟测试拦截名单的正则行为(见 smoke-test.mjs 里 DENY_EXTRA 带 /g 标志的回归用例)。
//
// --check-domain <url>(可重复传):纯 isLeftDomain() 校验钩子,不碰 agent-browser、不建 OUT
//   目录,用于冒烟测试逐击域名校验的判定逻辑。
//
// 域名边界(两层,详见 SKILL.md「安全边界」——0.27.0 实测过的如实表述):
//   1) --allowed-domains 只约束 agent-browser 的显式导航(`open`/`back`/`forward` 这类命令);
//      点击触发的同窗口跳转(location.href、<a href> 默认行为等)拦不住,且该 flag 只在
//      浏览器进程首次启动时生效——已运行的会话 / state 预载产生的会话不会因为后续命令换了
//      --allowed-domains 值而重新生效。这两点均已用本机 localhost 双端口实测验证(见 SKILL.md)。
//   2) 可靠边界靠引擎自己逐击校验:每次点击后解析 urlAfter 的 hostname,不在 ALLOWED_DOMAINS
//      集合内就记 left-domain 并立即强制 restore(screen) 拉回现场,不等下一次循环。
import { execFileSync } from 'node:child_process';
import { writeFileSync, appendFileSync, mkdirSync, existsSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

// ui-sweep 拥有的隔离会话名——不用 agent-browser 默认会话,避免动到用户自己开着的会话
// (0.27.0 实测:`--session <name>` 是独立会话,close 只关这个名字,不碰 default 或其他会话)。
const SESSION_NAME = 'ui-sweep';

// ---- 默认拦截名单(安全底线,config 只能通过 DENY_EXTRA 叠加,不可削减/覆盖) ----
const DENY_DEFAULT = /(吊销|解散|删除|退出|logout|sign ?out|revoke|归档|archive|清除|clear|重置|reset|发送|send|保存|save|上传|upload)/i;

// ---- CLI 参数 ----
const argv = process.argv.slice(2);
const STRICT = argv.includes('--strict');
const CHECK_CONFIG_ONLY = argv.includes('--check-config');
// configPath 约定为第一个非 flag 参数(argv[0]);之后 --check-deny <name> 的 <name> 也不以
// -- 开头,但 .find() 只取第一个匹配,不受它影响。
const configPath = argv.find((a) => !a.startsWith('--'));

if (!configPath) {
  console.error('Usage: node sweep.mjs <path>/sweep.config.mjs [--strict] [--check-config]');
  process.exit(1);
}

const configAbs = path.resolve(configPath);
const configDir = path.dirname(configAbs);

let config;
try {
  config = await import(pathToFileURL(configAbs).href);
} catch (e) {
  console.error(`config failed to load: ${configAbs}\n${e.message}`);
  process.exit(1);
}

const { ROOT, SCREENS, DENY_EXTRA, ALLOWED_DOMAINS: ALLOWED_DOMAINS_CFG, STATE_FILE, ensureBaseline, OUT: OUT_CFG } = config;

// ---- 必填项校验:缺失立即报错退出,不静默空跑 ----
const configErrors = [];
if (!ROOT || typeof ROOT !== 'string') {
  configErrors.push('missing required field ROOT (string, the starting URL)');
}
if (!Array.isArray(SCREENS) || SCREENS.length === 0) {
  configErrors.push('missing required field SCREENS (non-empty array of {id, path, settleMs?})');
}
if (DENY_EXTRA !== undefined && !(DENY_EXTRA instanceof RegExp)) {
  configErrors.push('DENY_EXTRA, if provided, must be a RegExp');
}
if (ALLOWED_DOMAINS_CFG !== undefined && (typeof ALLOWED_DOMAINS_CFG !== 'string' || !ALLOWED_DOMAINS_CFG)) {
  configErrors.push('ALLOWED_DOMAINS, if provided, must be a non-empty string (comma-separated domain patterns passed to agent-browser --allowed-domains)');
}
if (STATE_FILE !== undefined && (typeof STATE_FILE !== 'string' || !STATE_FILE)) {
  configErrors.push('STATE_FILE, if provided, must be a non-empty string (path to a state.json produced by export-state.mjs)');
}
if (ensureBaseline !== undefined && typeof ensureBaseline !== 'function') {
  configErrors.push('ensureBaseline, if provided, must be an async function');
}
if (configErrors.length) {
  console.error(`sweep.config.mjs validation failed (${configAbs}):`);
  for (const e of configErrors) console.error('  - ' + e);
  process.exit(1);
}

// ---- ALLOWED_DOMAINS 缺省从 ROOT 的 hostname 推导(F3:实证 agent-browser 全局 flag
//      `--allowed-domains <list>`/env AGENT_BROWSER_ALLOWED_DOMAINS = "Restrict navigation
//      domains",逗号分隔的域名 pattern,作为全局 flag 放在子命令之前传给每次调用) ----
let ALLOWED_DOMAINS = ALLOWED_DOMAINS_CFG;
if (!ALLOWED_DOMAINS) {
  try {
    ALLOWED_DOMAINS = new URL(ROOT).hostname;
  } catch (e) {
    console.error(`ROOT is not a valid URL and ALLOWED_DOMAINS was not provided: ${e.message}`);
    process.exit(1);
  }
}

// ---- ALLOWED_DOMAINS 解析成一份 pattern 列表,供引擎自己的 isLeftDomain() 逐击校验用
//      (与传给 agent-browser --allowed-domains 的原始字符串是同一份数据,只是这里额外
//      解析一次给纯函数用——见文件头「域名边界」注释,这是可靠层,不是 agent-browser 那层)。
//      支持精确 hostname 匹配与 `*.example.com` 前缀通配;逗号分隔,两端空白会被裁剪。
const ALLOWED_DOMAIN_PATTERNS = ALLOWED_DOMAINS.split(',').map((s) => s.trim()).filter(Boolean);

function isLeftDomain(url) {
  let hostname = '';
  try { hostname = new URL(url).hostname; } catch { return false; } // about:blank 等不可解析 URL 不算逃逸信号
  if (!hostname) return false;
  const allowed = ALLOWED_DOMAIN_PATTERNS.some((p) => {
    if (p.startsWith('*.')) return hostname === p.slice(2) || hostname.endsWith(p.slice(1));
    return hostname === p;
  });
  return !allowed;
}

if (CHECK_CONFIG_ONLY) {
  console.log(`config OK: ROOT=${ROOT} SCREENS=${SCREENS.length} DENY_EXTRA=${DENY_EXTRA ? 'yes' : 'no'} ALLOWED_DOMAINS=${ALLOWED_DOMAINS} STATE_FILE=${STATE_FILE || 'no'} ensureBaseline=${ensureBaseline ? 'yes' : 'no'}`);
  process.exit(0);
}

// ---- DENY_EXTRA 规格化(F2 安全修复):RegExp.prototype.test() 在 /g 或 /y(sticky)标志下
//      会推进 lastIndex,同一个 RegExp 实例被反复 .test() 同一个字符串时会交替 true/false
//      (隔一个漏一个),导致同名破坏性按钮被真点。config 校验通过后立即剥离这两个标志重建。 ----
const DENY_EXTRA_SAFE = DENY_EXTRA instanceof RegExp
  ? new RegExp(DENY_EXTRA.source, DENY_EXTRA.flags.replace(/[gy]/g, ''))
  : undefined;

function isDenied(name) {
  if (DENY_DEFAULT.test(name)) return true;
  if (DENY_EXTRA_SAFE instanceof RegExp && DENY_EXTRA_SAFE.test(name)) return true;
  return false;
}

// ---- --check-deny <name>(可重复):纯函数校验,不碰 agent-browser、不建 OUT 目录 ----
const denyCheckNames = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--check-deny') denyCheckNames.push(argv[i + 1]);
}
if (denyCheckNames.length) {
  console.log(JSON.stringify(denyCheckNames.map((n) => ({ name: n, denied: isDenied(n) }))));
  process.exit(0);
}

// ---- --check-domain <url>(可重复):纯函数校验,不碰 agent-browser、不建 OUT 目录 ----
const domainCheckUrls = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--check-domain') domainCheckUrls.push(argv[i + 1]);
}
if (domainCheckUrls.length) {
  console.log(JSON.stringify(domainCheckUrls.map((u) => ({ url: u, leftDomain: isLeftDomain(u) }))));
  process.exit(0);
}

// ---- 输出目录(默认 ./sweep-out,相对 config 所在目录) ----
const OUT = path.resolve(configDir, OUT_CFG || './sweep-out') + path.sep;
mkdirSync(OUT, { recursive: true });
// F9:sweep-out 含截图与台账(可能带业务数据),整目录不入 git;已存在就不覆盖
// (用户可能已经在这份 .gitignore 里手写了别的规则,引擎不该把它冲掉)。
const GITIGNORE = OUT + '.gitignore';
if (!existsSync(GITIGNORE)) writeFileSync(GITIGNORE, '*\n');
const LEDGER = OUT + 'ledger.jsonl';
writeFileSync(LEDGER, '');

function ab(args, { json = false, ok = false } = {}) {
  const full = ['--session', SESSION_NAME, '--allowed-domains', ALLOWED_DOMAINS, ...args, ...(json ? ['--json'] : [])];
  try {
    const out = execFileSync('agent-browser', full, { encoding: 'utf8', timeout: 45000 });
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

// ---- 引擎接管会话生命周期(D1a 工程兜底):sweep 启动时先 close 掉 ui-sweep 这个隔离
//      会话名下可能残留的旧进程,再用带 --allowed-domains 的命令重新建会话——
//      这样 --allowed-domains 才真正对本次跑的浏览器进程生效(0.27.0 实测:该 flag 只在
//      浏览器进程启动那一刻生效,已运行的会话不会因后续命令换了值而重新生效;旧流程让用户
//      在跑引擎前手动 `agent-browser state load` 预载登录态,如果那条命令先把会话建起来了,
//      引擎自己的 --allowed-domains 就成了没人听的空话——这正是本轮修复的诱因)。
//      `close` 用 { ok: true }:第一次跑没有残留会话时 close 会报错,忽略即可,不是异常。
async function initSession() {
  ab(['close'], { ok: true });
  ab(['open', ROOT]);
  await settle(2000);
  if (STATE_FILE) {
    const r = ab(['state', 'load', STATE_FILE]);
    if (r && r.__err) {
      console.error(`STATE_FILE failed to load: ${STATE_FILE}\n${r.__err}`);
      process.exit(1);
    }
    await settle(1000);
  }
}

async function restore(screen) {
  ab(['open', ROOT]);
  await settle(2000);
  // 项目相关的基线钩子(如某项目的语言锁):由 config 的 ensureBaseline 提供,引擎本身不内置任何项目专属逻辑
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
  const raw = String(r).trim();
  // `eval` 的字符串结果是 JSON 序列化过的(带引号,本机实测:`agent-browser eval "location.href"`
  // 输出 `"http://…"`),split('|') 前必须先脱一层引号,否则第一段 url 前会挂着一个杂散的
  // `"`,new URL() 解析直接抛错——isLeftDomain() 依赖能干净解析出 hostname,这层脱壳是前提。
  try { return String(JSON.parse(raw)); } catch { return raw; }
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

await initSession();

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
    const urlAfter = after.split('|')[0];
    const changed = before !== after;
    // D1b 可靠层:--allowed-domains 只挡显式导航,挡不住点击触发的同窗口跳转
    // (0.27.0 实测,见文件头「域名边界」注释)——逐击解析 urlAfter 的 hostname,
    // 不在 ALLOWED_DOMAINS 集合内就判 left-domain,并且这条分类优先于其他分类,
    // 因为它是安全边界问题,不是产品行为问题。
    const outOfDomain = isLeftDomain(urlAfter);
    let result = 'dead';
    if (outOfDomain) result = 'left-domain';
    else if (clickErr) result = 'click-error';
    else if (pageErrors) result = 'page-error';
    else if (dialog) result = 'dialog-dismissed';
    else if (changed) result = 'ok-changed';
    log({ screen: screen.id, k, name: want.name, role: want.role, result, clickErr, dialog, pageErrors, consoleIssues, urlAfter });
    console.log(`  [${k}] ${want.role} "${want.name}" -> ${result}`);
    if (outOfDomain) {
      // 当场强制拉回,不等下一次循环开头的 dirty/--strict 判断——出域是安全事件,不能拖到下一击。
      if (!(await restore(screen))) { log({ screen: screen.id, k, result: 'restore-failed-after-left-domain' }); break; }
      dirty = false;
    } else {
      dirty = changed || !!dialog;
    }
  }
}

console.log('SWEEP DONE, ledger:', LEDGER);
