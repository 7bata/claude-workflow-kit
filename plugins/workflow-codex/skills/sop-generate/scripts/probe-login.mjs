import { chromium } from 'playwright';
// close() 最多等 10 秒:卡住时打一行提示并继续,脚本随后显式退出(playwright 在进程退出时会结束浏览器子进程;
// Browser 对象拿不到子进程 PID,所以不按 PID 结束)。
const CLOSE_TIMEOUT_MS = 10000;
let closeTimedOut = false;
async function closeBounded(b) {
  let timer;
  const timeout = new Promise((resolve) => { timer = setTimeout(() => resolve('timeout'), CLOSE_TIMEOUT_MS); });
  const closed = b.close().then(() => 'closed', () => 'closed');
  const r = await Promise.race([closed, timeout]);
  clearTimeout(timer);
  if (r === 'timeout') {
    closeTimedOut = true;
    console.error(`closing the browser took longer than ${CLOSE_TIMEOUT_MS / 1000}s and it may not have closed; check with ps for a leftover browser process`);
  }
}
const b = await chromium.launch();
let failed = false;
let failure = null;
try {
  const p = await b.newPage();
  await p.goto(process.argv[2], { waitUntil: 'networkidle' });
  const inputs = await p.$$eval('input, button', els => els.map(e => ({tag: e.tagName, type: e.type, name: e.name, id: e.id, ph: e.placeholder, text: e.textContent?.trim().slice(0,20)})));
  console.log(JSON.stringify(inputs, null, 1));
} catch (e) {
  failed = true;
  failure = e;
  throw e;
} finally {
  await closeBounded(b);
  // close 超时时连接可能让进程不退出:按原本应有的退出码显式退出(出错 1,否则 0)
  if (closeTimedOut) { if (failed) console.error('probe-login failed:', failure); process.exit(failed ? 1 : 0); }
}
