import { chromium } from 'playwright';
const b = await chromium.launch(); const p = await b.newPage();
await p.goto(process.argv[2], { waitUntil: 'networkidle' });
const inputs = await p.$$eval('input, button', els => els.map(e => ({tag: e.tagName, type: e.type, name: e.name, id: e.id, ph: e.placeholder, text: e.textContent?.trim().slice(0,20)})));
console.log(JSON.stringify(inputs, null, 1));
await b.close();
