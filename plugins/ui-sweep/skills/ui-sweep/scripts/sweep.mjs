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
//   export const INVENTORY = {                        // 可选,配了才启用「孤儿功能对账」;
//     apis: ['GET /api/projects', 'POST /api/projects/:id/archive'], // 方法+路径模式字符串数组
//     routes: ['/dashboard', '/projects/:id'],          // 前端路由模式字符串数组
//     exempt: [/^POST \/api\/webhooks/, /^GET \/health$/], // 正则数组,预期无 UI 入口
//   };                                                 // 三个子字段全部可选;不配 INVENTORY 时
//                                                       // 对账逻辑整体短路,行为与现状完全一致。
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
// --check-normalize-api <METHOD> <URL>(可重复传,成对出现):纯 normalizeApi() 校验钩子,
//   不碰 agent-browser、不建 OUT 目录,用于冒烟测试 URL 归一化(数字/UUID/长 hex → :id)。
//
// --check-normalize-route <url-or-pathname>(可重复传):纯 normalizeRoute() 校验钩子,同上。
//
// --check-orphan-diff <jsonSeenPayload>:纯 diffOrphans() 校验钩子,INVENTORY 取自 config,
//   seenApis/seenRoutes 取自 CLI 传入的 JSON(形如
//   {"seenApis":{"GET /api/x/:id":200},"seenRoutes":["/dashboard"]});不碰 agent-browser、
//   不建 OUT 目录,用于冒烟测试差集(unreachable/broken/exempt_hits)纯函数。
//
// --check-parse-network <jsonPayload>:纯 extractNetworkRequests()+accumulateSeenApis() 校验
//   钩子,喂一段 `agent-browser network requests --json` 的真实响应样本(不碰 agent-browser
//   本身),断言能从其形状里正确解出 requests 数组并归一化进 seenApis 结构。用于回归"采集函数
//   解析了错误的 JSON 形状导致整条对账功能静默失效"这类问题——agent-browser 0.x 实测返回的是
//   {"success":true,"data":{"requests":[...]},"error":null},不是裸数组。这条钩子与
//   collectNetworkRequests() 共用 accumulateSeenApis(),因此也覆盖"出域/第三方请求条目
//   不进 seenApis"(第三轮 G1)这条回归——喂含外站 URL 的样本即可断言。
//
// --check-coverage-note <jsonPayload>:纯 buildCoverageNote() 校验钩子,payload 形如
//   {"coverageGaps":["home"],"networkParseFailureCount":2,"networkCollectionAttempts":5};
//   用于冒烟测试「采集失灵(解析失败次数>0)或整轮零采集(采集次数=0)时,coverage_note 必须
//   带警告文字、且绝不能输出 full coverage 强断言」。不碰 agent-browser、不建 OUT 目录。
//
// 注意(工具钩子不可组合):上述各 --check-* 钩子按本文件里出现的先后顺序短路 return——
//   同一条命令里传了多个不同的 --check-* 旗标,只有排在前面的那个会执行并 exit,后面的会被
//   忽略。这只影响冒烟/手测的便利性(每种钩子请单独起一条命令),不影响引擎主流程。
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

// ---- 默认拦截名单(安全底线,config 只能通过 DENY_EXTRA 叠加,不可削减/覆盖)----
// 2026-08-13 补:实测英文 UI 的 <button>Delete item</button> 会被真点、POST 真发出——旧正则
// 只有中文「删除」没有英文 delete,英文站点的破坏性删除类按钮完全漏过拦截。补齐
// delete/remove/dissolve/discard/drop,与本 SKILL.md「安全边界」一节「each matched in both
// English and Chinese」的既有声明对齐(该声明此前对不少词其实是假的)。
const DENY_DEFAULT = /(吊销|解散|删除|退出|logout|sign ?out|revoke|归档|archive|清除|clear|重置|reset|发送|send|保存|save|上传|upload|delete|remove|dissolve|discard|drop)/i;

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

const { ROOT, SCREENS, DENY_EXTRA, ALLOWED_DOMAINS: ALLOWED_DOMAINS_CFG, STATE_FILE, ensureBaseline, OUT: OUT_CFG, INVENTORY } = config;

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
// ---- INVENTORY(孤儿功能对账,全部可选;不配则该功能整体短路,行为与现状完全一致) ----
if (INVENTORY !== undefined) {
  if (typeof INVENTORY !== 'object' || INVENTORY === null || Array.isArray(INVENTORY)) {
    configErrors.push('INVENTORY, if provided, must be an object with optional apis/routes/exempt fields');
  } else {
    const { apis: invApis, routes: invRoutes, exempt: invExempt } = INVENTORY;
    if (invApis !== undefined && (!Array.isArray(invApis) || !invApis.every((s) => typeof s === 'string'))) {
      configErrors.push('INVENTORY.apis, if provided, must be an array of strings ("METHOD /path" patterns)');
    }
    if (invRoutes !== undefined && (!Array.isArray(invRoutes) || !invRoutes.every((s) => typeof s === 'string'))) {
      configErrors.push('INVENTORY.routes, if provided, must be an array of strings (frontend route patterns)');
    }
    if (invExempt !== undefined && (!Array.isArray(invExempt) || !invExempt.every((r) => r instanceof RegExp))) {
      configErrors.push('INVENTORY.exempt, if provided, must be an array of RegExp');
    }
  }
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

// ---- 孤儿功能对账(3.1~3.4):INVENTORY 未配时 INVENTORY_ENABLED=false,后续对账逻辑
//      全部短路(不清空 network requests、不采集、不写 orphan-audit 台账记录)——
//      行为与现状完全一致(验收条款 1)。 ----
const INVENTORY_ENABLED = !!INVENTORY;
const INVENTORY_NORM = INVENTORY_ENABLED
  ? { apis: INVENTORY.apis || [], routes: INVENTORY.routes || [], exempt: INVENTORY.exempt || [] }
  : null;

if (CHECK_CONFIG_ONLY) {
  // INVENTORY 字段只在配了 INVENTORY 时才追加到输出——未配 INVENTORY 时这一行必须与改动前
  // 逐字节一致(验收条款 1「未配 INVENTORY 时行为与现状完全一致」覆盖到 --check-config 的输出,
  // 下游若按字符串断言这一行不该因为本次改动而碰壁)。
  const inventoryField = INVENTORY_ENABLED ? ' INVENTORY=yes' : '';
  console.log(`config OK: ROOT=${ROOT} SCREENS=${SCREENS.length} DENY_EXTRA=${DENY_EXTRA ? 'yes' : 'no'} ALLOWED_DOMAINS=${ALLOWED_DOMAINS} STATE_FILE=${STATE_FILE || 'no'} ensureBaseline=${ensureBaseline ? 'yes' : 'no'}${inventoryField}`);
  process.exit(0);
}

// ---- normalizeApi / normalizeRoute(3.2 归一化):URL → 模式串,数字/UUID/长 hex 段替换
//      为 :id,query string 丢弃。纯函数,不碰 agent-browser、不联网。 ----
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const LONG_HEX_RE = /^[0-9a-f]{8,}$/i;
const DIGITS_RE = /^\d+$/;

function isIdSegment(seg) {
  if (!seg) return false;
  return DIGITS_RE.test(seg) || UUID_RE.test(seg) || LONG_HEX_RE.test(seg);
}

// url 可以是完整 URL,也可以是裸路径(如 location.pathname 已经取好的值)——两种都要能处理。
function normalizePathname(url) {
  let pathname = url;
  try { pathname = new URL(url).pathname; } catch { /* 不是完整 URL,当作裸路径处理 */ }
  pathname = pathname.split('?')[0].split('#')[0];
  const segments = pathname.split('/').map((seg) => (isIdSegment(seg) ? ':id' : seg));
  let normalized = segments.join('/');
  // 尾斜杠不归一化会导致前端路由假阳性(Astro/Next 等默认带尾斜杠的站点整片误报 unreachable)——
  // 非根路径去掉末尾 '/' 再比对;根路径 '/' 保留,不裁成空串。
  if (normalized.length > 1 && normalized.endsWith('/')) normalized = normalized.slice(0, -1);
  return normalized || '/';
}

function normalizeApi(method, url) {
  return `${String(method).toUpperCase()} ${normalizePathname(url)}`;
}

function normalizeRoute(url) {
  return normalizePathname(url);
}

// ---- accumulateSeenApis(第三轮 G1 修复,F5 只修了 seenRoutes 半边):collectNetworkRequests()
//      与 --check-parse-network 冒烟钩子共用同一份写入逻辑,不能分叉出两套过滤口径。
//      每条网络请求写进 seenApis 之前先套 isLeftDomain() 判定——不加这一层,出域/第三方请求
//      (埋点、Sentry、Stripe、Intercom、CDN 探活……真实站点必有)会被 normalizeApi() 丢掉
//      hostname、只留 pathname,与站内同 pathname 的请求撞进同一个 key:轻则把站内真孤儿 API
//      顶掉(seenApis 里已有这条 key,unreachable 判定漏报),重则把第三方的 4xx/5xx 状态码
//      假冒成站内 API 的 broken-entry。与 seenRoutes 那半边(见 recordScreenEntry/循环体内
//      isLeftDomain 判定注释)必须是同一套口径,不留特例。 ----
function accumulateSeenApis(reqs, seenApis) {
  for (const r of reqs) {
    if (!r || !r.method || !r.url) continue;
    if (isLeftDomain(r.url)) continue;
    seenApis[normalizeApi(r.method, r.url)] = r.status;
  }
}

// ---- diffOrphans(3.3 差集):INVENTORY 声明的 apis/routes 与实际采集到的 seenApis/seenRoutes
//      求差集;exempt 命中的条目只计数、不计入 unreachable;broken 取 seenApis 里 status>=400
//      的条目(含未在 INVENTORY 里的,一并报——它们同样是真实的坏入口)。纯函数。 ----
function diffOrphans(inventory, seenApis, seenRoutes) {
  const apis = inventory.apis || [];
  const routes = inventory.routes || [];
  const exempt = inventory.exempt || [];
  const seenRouteSet = new Set(seenRoutes || []);
  const isExempt = (key) => exempt.some((re) => re.test(key));

  const exemptHits = [];
  const unreachable = [];
  for (const key of apis) {
    if (isExempt(key)) { exemptHits.push(key); continue; }
    if (!(key in (seenApis || {}))) unreachable.push(key);
  }
  for (const key of routes) {
    if (isExempt(key)) { exemptHits.push(key); continue; }
    if (!seenRouteSet.has(key)) unreachable.push(key);
  }
  const broken = Object.entries(seenApis || {})
    .filter(([, status]) => Number(status) >= 400)
    .map(([key, status]) => ({ key, status }));

  return { unreachable, broken, exemptHits };
}

// ---- extractNetworkRequests(3.2 采集,解析防御):`agent-browser network requests --json`
//      实测(0.x)返回的形状是 {"success":true,"data":{"requests":[...]},"error":null},不是
//      裸数组——之前一版按 Array.isArray(reqs) 直接判定,恒为 false,导致 seenApis 永远为空、
//      对账功能整条静默死掉。这里同时兼容"直接就是数组"与"包在 data.requests / requests 里"
//      两种形状;解析不出任何数组时返回空数组,并打印一次(仅一次)告警——宁可吵一声也不要
//      同类形状再变更时又被静默吞掉。纯函数,不碰 agent-browser。 ----
let networkShapeWarned = false;
// networkParseFailureCount (F3): every time this function can't make sense of the payload shape,
// it counts — not just the first time (networkShapeWarned only gates the printed warning to once,
// so log spam doesn't drown out the ledger). The main loop reads this counter after the run to
// decide whether the orphan-audit conclusion is trustworthy (see buildCoverageNote()).
let networkParseFailureCount = 0;
function extractNetworkRequests(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.data?.requests)) return payload.data.requests;
  if (payload && Array.isArray(payload.requests)) return payload.requests;
  networkParseFailureCount++;
  if (!networkShapeWarned) {
    networkShapeWarned = true;
    const shape = payload && typeof payload === 'object' ? Object.keys(payload).join(',') : typeof payload;
    console.error(`warning: could not parse "network requests --json" output (expected an array or {data:{requests:[...]}}); orphan-audit API coverage will be incomplete. payload top-level keys: ${shape}`);
  }
  return [];
}

// ---- buildCoverageNote (F3 采集失灵不可辨 / 覆盖缺口不可辨):orphan-audit 的 coverage_note
//      不能只报「哪些屏 restore 失败」——采集函数本身解析失败(networkParseFailureCount>0),
//      或整轮压根没成功跑过一次采集(networkCollectionAttempts===0),都意味着 unreachable
//      结论不可信,必须在这里明说,并且这两种情况下绝不能输出「full coverage」这种强断言
//      (即便所有屏都 restore 成功、coverageGaps 是空的)。纯函数,便于冒烟测试覆盖各分支。 ----
function buildCoverageNote({ coverageGaps = [], networkParseFailureCount = 0, networkCollectionAttempts = 0 }) {
  const notes = [];
  if (coverageGaps.length) {
    notes.push(`incomplete coverage on screen(s): ${coverageGaps.join(', ')} — unreachable entries reachable only via these screens are not conclusive`);
  }
  if (networkParseFailureCount > 0) {
    notes.push(`network collection failed: ${networkParseFailureCount} time(s) could not parse "network requests --json" output — unreachable/broken-entry conclusions for APIs are not trustworthy`);
  } else if (networkCollectionAttempts === 0) {
    notes.push('network collection never ran (0 attempts across the whole run) — unreachable conclusions for APIs are not trustworthy');
  }
  return notes.length ? notes.join('; ') : 'full coverage: all screens completed without restore failures';
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

// ---- --check-normalize-api <METHOD> <URL>(可重复,成对):纯 normalizeApi() 校验 ----
const normalizeApiChecks = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--check-normalize-api') normalizeApiChecks.push([argv[i + 1], argv[i + 2]]);
}
if (normalizeApiChecks.length) {
  console.log(JSON.stringify(normalizeApiChecks.map(([method, url]) => ({ method, url, normalized: normalizeApi(method, url) }))));
  process.exit(0);
}

// ---- --check-normalize-route <url-or-pathname>(可重复):纯 normalizeRoute() 校验 ----
const normalizeRouteChecks = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--check-normalize-route') normalizeRouteChecks.push(argv[i + 1]);
}
if (normalizeRouteChecks.length) {
  console.log(JSON.stringify(normalizeRouteChecks.map((url) => ({ url, normalized: normalizeRoute(url) }))));
  process.exit(0);
}

// ---- --check-orphan-diff <jsonSeenPayload>:纯 diffOrphans() 校验,INVENTORY 取自 config ----
const orphanDiffIdx = argv.indexOf('--check-orphan-diff');
if (orphanDiffIdx !== -1) {
  let payload;
  try {
    payload = JSON.parse(argv[orphanDiffIdx + 1]);
  } catch (e) {
    console.error(`--check-orphan-diff payload is not valid JSON: ${e.message}`);
    process.exit(1);
  }
  if (!INVENTORY_ENABLED) {
    console.error('--check-orphan-diff requires config to export INVENTORY');
    process.exit(1);
  }
  const result = diffOrphans(INVENTORY_NORM, payload.seenApis || {}, payload.seenRoutes || []);
  console.log(JSON.stringify(result));
  process.exit(0);
}

// ---- --check-parse-network <jsonPayload>:纯 extractNetworkRequests()+normalizeApi() 校验,
//      不碰 agent-browser、不建 OUT 目录。喂一段 agent-browser 的真实响应样本(如实测的
//      {"success":true,"data":{"requests":[...]},"error":null}),断言能解出 seenApis 条目——
//      回归"采集函数解析了错误的 JSON 形状,对账功能整条死掉"这类 bug。 ----
const parseNetworkIdx = argv.indexOf('--check-parse-network');
if (parseNetworkIdx !== -1) {
  let payload;
  try {
    payload = JSON.parse(argv[parseNetworkIdx + 1]);
  } catch (e) {
    console.error(`--check-parse-network payload is not valid JSON: ${e.message}`);
    process.exit(1);
  }
  const reqs = extractNetworkRequests(payload);
  const seen = {};
  accumulateSeenApis(reqs, seen);
  console.log(JSON.stringify(seen));
  process.exit(0);
}

// ---- --check-coverage-note <jsonPayload>:纯 buildCoverageNote() 校验钩子,不碰
//      agent-browser、不建 OUT 目录。payload 形如
//      {"coverageGaps":["home"],"networkParseFailureCount":2,"networkCollectionAttempts":5}——
//      用于冒烟测试「采集失灵/整轮零采集时 coverage_note 必须带警告、且绝不能输出
//      full coverage 强断言」(F3)。 ----
const coverageNoteIdx = argv.indexOf('--check-coverage-note');
if (coverageNoteIdx !== -1) {
  let payload;
  try {
    payload = JSON.parse(argv[coverageNoteIdx + 1]);
  } catch (e) {
    console.error(`--check-coverage-note payload is not valid JSON: ${e.message}`);
    process.exit(1);
  }
  console.log(JSON.stringify({ coverage_note: buildCoverageNote(payload || {}) }));
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

// ---- 孤儿功能对账(3.2 采集):全局累积,跨屏不清空;INVENTORY 未配时这些变量始终空,
//      下方所有读写都套在 INVENTORY_ENABLED 判断里,零副作用。 ----
const seenApis = {}; // 归一化后的 "METHOD /path" -> 最后一次见到的 status
const seenRoutes = new Set(); // 归一化后的前端路由 pathname
const coverageGaps = []; // 出现 restore 失败/miss-not-found 等覆盖缺口的屏 id(诚实记账,见 spec 3.4)
let networkCollectionAttempts = 0; // collectNetworkRequests() 被调用的次数(F3:整轮为 0 说明采集从未真正跑过)
let totalRequestsSeen = 0; // 所有采集里解出的 request 条目累计数(仅供诊断,不进 coverage_note)

// 只读页(0 可点元素)/纯展示屏的 route 若只在「每击后」采集,永远进不了 seenRoutes——F1 修复:
// restore 成功后立刻调一次,不依赖后续有没有点击。同一批顺手把 mount 期的 XHR/fetch 收进
// seenApis——F2 修复:SPA 最常见的「mount 期 GET」发生在 restore 期间,若 --clear 挪到
// restore 之后,这些请求会被直接清空、永远进不了账。两件事合并成一个函数,避免调用点重复。
function recordScreenEntry(urlNow) {
  collectNetworkRequests();
  // F5:出域的 URL 不计入 seenRoutes——顶掉站内真孤儿路由的账。restore() 内部先 `open(ROOT)`
  // 才走 screen.path,理论上不会真的出域,但仍然套上同一条 isLeftDomain() 判定,和逐击那处
  // 判定同一套口径,不留特例。
  if (!isLeftDomain(urlNow)) seenRoutes.add(normalizeRoute(urlNow));
}

// 每击后取一次 network requests 增量,归一化累积进 seenApis。
// `--type xhr,fetch` 把 Document/Image/Other 等资源类型过滤掉——不加这个过滤,favicon.ico
// 一类的静态资源 404 会混进 seenApis,broken-entry 一节信噪比很低。
// 解析用 extractNetworkRequests():agent-browser 0.x 实测返回的是
// {"success":true,"data":{"requests":[...]},"error":null},不是裸数组。
// 写入用 accumulateSeenApis():每条请求先套 isLeftDomain() 判定,出域/第三方请求不进
// seenApis(第三轮 G1 修复——见 accumulateSeenApis 定义处注释)。
function collectNetworkRequests() {
  networkCollectionAttempts++;
  // ab(..., { json: true }) already appends --json itself (see ab() below) — passing it again
  // here was a harmless-but-redundant duplicate flag on the agent-browser CLI invocation.
  const payload = ab(['network', 'requests', '--type', 'xhr,fetch'], { json: true, ok: true });
  const reqs = extractNetworkRequests(payload);
  totalRequestsSeen += reqs.length;
  accumulateSeenApis(reqs, seenApis);
}

await initSession();

for (const screen of SCREENS) {
  console.log('=== SCREEN', screen.id);
  // F2:--clear 必须排在 restore 之前——restore() 内部会 open(ROOT) 并走 screen.path,这正是
  // SPA mount 期 XHR/fetch 发生的窗口;--clear 排在 restore 之后会把这些请求连本带利清空,
  // 采集功能对「mount 期 GET」这个最主流场景永远失灵,且行为随现场脏不脏而漂移。
  if (INVENTORY_ENABLED) ab(['network', 'requests', '--clear'], { ok: true });
  if (!(await restore(screen))) { log({ screen: screen.id, result: 'screen-restore-failed' }); console.log('RESTORE FAIL'); if (INVENTORY_ENABLED) coverageGaps.push(screen.id); continue; }
  if (INVENTORY_ENABLED) recordScreenEntry(fingerprint().split('|')[0]);
  ab(['screenshot', OUT + screen.id + '.png'], { ok: true });
  grabErrors(); // 清掉加载期噪音,单独记屏级
  const plan = snapshotPlan().filter((e) => CLICK_ROLES.has(e.role));
  console.log('elements:', plan.length);
  log({ screen: screen.id, result: 'screen-plan', count: plan.length, names: plan.map((p) => p.name).slice(0, 60) });

  let dirty = false; // 上一个点击是否改变了状态(需要恢复);--strict 下无条件每击恢复
  for (let k = 0; k < plan.length; k++) {
    const want = plan[k];
    if (isDenied(want.name)) { log({ screen: screen.id, k, name: want.name, role: want.role, result: 'skipped-denylist' }); continue; }
    if (STRICT || dirty) { if (!(await restore(screen))) { log({ screen: screen.id, k, result: 'restore-failed' }); if (INVENTORY_ENABLED) coverageGaps.push(screen.id); break; } dirty = false; }
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
    if (!target) {
      log({ screen: screen.id, k, name: want.name, role: want.role, result: 'miss-not-found' });
      // F3(覆盖缺口不只算 restore-failed):miss-not-found 同样意味着这一击没有真的发生过——
      // 该屏若有 API 只可能由这个丢失的目标触发,unreachable 结论同样不可信,须计入 coverageGaps。
      if (INVENTORY_ENABLED) coverageGaps.push(screen.id);
      continue;
    }
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
    // 孤儿功能对账(3.2):同一批(与指纹采集同批)取增量网络请求,不额外多起命令。
    if (INVENTORY_ENABLED) collectNetworkRequests();
    // D1b 可靠层:--allowed-domains 只挡显式导航,挡不住点击触发的同窗口跳转
    // (0.27.0 实测,见文件头「域名边界」注释)——逐击解析 urlAfter 的 hostname,
    // 不在 ALLOWED_DOMAINS 集合内就判 left-domain,并且这条分类优先于其他分类,
    // 因为它是安全边界问题,不是产品行为问题。
    const outOfDomain = isLeftDomain(urlAfter);
    // F5:seenRoutes 只收站内路由——outOfDomain 的 URL 若也 add 进去,一条外站路径就能顶掉
    // 一条真正的站内孤儿路由(Set 里两个不同 host 的同 pathname 会被当成"这条路由被访问过")。
    // 必须放在 isLeftDomain() 判定之后,不能像本轮修复前那样排在判定之前无条件 add。
    if (INVENTORY_ENABLED && !outOfDomain) seenRoutes.add(normalizeRoute(urlAfter));
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
      if (!(await restore(screen))) { log({ screen: screen.id, k, result: 'restore-failed-after-left-domain' }); if (INVENTORY_ENABLED) coverageGaps.push(screen.id); break; }
      dirty = false;
    } else {
      dirty = changed || !!dialog;
    }
  }
}

// ---- 孤儿功能对账(3.4):遍历结束后写一条全局结论记录,不进现有八分类。
//      第三轮 G3 修复:seen_count(全部观测条目,含不在 INVENTORY 里的)不是覆盖率分子、
//      inventory_count(含 exempt,天然不可达)也不是覆盖率分母——旧字段名把两者硬凑成
//      seen/inventory 呈现,exempt 占比一高就能 >100%,读起来像坏数据。
//      分子换成 inventory_hit_count(INVENTORY 里非 exempt 条目、且实际被命中的数量 =
//      auditable 减去 unreachable),分母换成 inventory_auditable_count(INVENTORY 总数减
//      exempt);seen_count 保留,但只作为"总观测数"另列,不参与覆盖率计算。 ----
if (INVENTORY_ENABLED) {
  const { unreachable, broken, exemptHits } = diffOrphans(INVENTORY_NORM, seenApis, [...seenRoutes]);
  const inventoryAuditableCount = INVENTORY_NORM.apis.length + INVENTORY_NORM.routes.length - exemptHits.length;
  const inventoryHitCount = inventoryAuditableCount - unreachable.length;
  const seenCount = Object.keys(seenApis).length + seenRoutes.size; // 总观测数(含非 INVENTORY 条目),不是覆盖率分子
  const uniqueGaps = [...new Set(coverageGaps)];
  const coverageNote = buildCoverageNote({
    coverageGaps: uniqueGaps,
    networkParseFailureCount,
    networkCollectionAttempts,
  });
  log({
    type: 'orphan-audit',
    unreachable,
    broken,
    exempt_hits: exemptHits,
    seen_count: seenCount,
    inventory_hit_count: inventoryHitCount,
    inventory_auditable_count: inventoryAuditableCount,
    coverage_note: coverageNote,
  });
}

console.log('SWEEP DONE, ledger:', LEDGER);
