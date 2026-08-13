#!/usr/bin/env node
// 从真实浏览器(CDP)导出登录态 → {cookies, origins:[{origin, localStorage}]} JSON(值不打印到 stdout)
//
// 用法:
//   node export-state.mjs --cdp <http://host:port> --out <path/to/state.json> --origin <origin> [--origin <origin> ...]
//
// 三项均必填,缺任一项立即报错退出:
//   --cdp     Chrome DevTools Protocol 地址(如 http://127.0.0.1:9222)
//   --out     导出文件写入路径
//   --origin  要导出 localStorage 的 origin,可重复传多个
import { writeFileSync } from 'node:fs';
import { chromium } from 'playwright-core';

function parseArgs(argv) {
  const out = { origins: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--cdp') out.cdp = argv[++i];
    else if (a === '--out') out.out = argv[++i];
    else if (a === '--origin') out.origins.push(argv[++i]);
  }
  return out;
}

const { cdp, out, origins } = parseArgs(process.argv.slice(2));

const errors = [];
if (!cdp) errors.push('缺少必填参数 --cdp <http://host:port>');
if (!out) errors.push('缺少必填参数 --out <path/to/state.json>');
if (!origins.length) errors.push('缺少必填参数 --origin <origin>(至少一个,可重复传多个)');
if (errors.length) {
  console.error('export-state.mjs 参数校验失败:');
  for (const e of errors) console.error('  - ' + e);
  console.error('用法: node export-state.mjs --cdp <http://host:port> --out <path> --origin <origin> [--origin <origin> ...]');
  process.exit(1);
}

const browser = await chromium.connectOverCDP(cdp);
const ctx = browser.contexts()[0];
if (!ctx) {
  console.error(`CDP 连上了但没有可用的浏览器上下文: ${cdp}`);
  await browser.close();
  process.exit(1);
}

const cookies = await ctx.cookies();

const originStates = [];
for (const origin of origins) {
  let page = ctx.pages().find((p) => p.url().startsWith(origin));
  let opened = false;
  if (!page) { page = await ctx.newPage(); await page.goto(origin, { waitUntil: 'domcontentloaded' }).catch(() => {}); opened = true; }
  const ls = await page.evaluate(() => {
    const items = [];
    for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); items.push({ name: k, value: localStorage.getItem(k) || '' }); }
    return items;
  }).catch(() => []);
  originStates.push({ origin, localStorage: ls });
  if (opened) await page.close().catch(() => {});
}

writeFileSync(out, JSON.stringify({ cookies, origins: originStates }, null, 1), { mode: 0o600 });
console.log('written:', out, '| cookies:', cookies.length, '| origins:', originStates.map((o) => o.origin + '(' + o.localStorage.length + ' keys)').join(', '));
await browser.close();
