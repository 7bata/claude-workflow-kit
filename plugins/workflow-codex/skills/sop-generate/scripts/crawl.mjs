#!/usr/bin/env node
/**
 * sop-generate 采集脚本 — 原生 Playwright 版(默认技术路线)
 *
 * 若当前环境已配置浏览器类 MCP(如 playwright 系),可自行改用其工具代替本脚本
 * (见 SKILL.md「技术路线」一节的「可选替代」)。
 * 三段式:登录 → 遍历 → 截图。脚本只产出截图文件 + 每页的 accessibility 摘要 JSON,
 * 不写文案 —— 文案由调用方读摘要 JSON 生成,严禁把整页截图喂给模型。
 *
 * 用法(cwd 通常是被测项目根目录,务必用绝对路径调用本脚本):
 *   SOP_USER='<测试账号用户名>' SOP_PASS='<测试账号密码>' \
 *   node <本 skill base directory>/scripts/crawl.mjs \
 *     --url https://internal-app.example \
 *     --out docs/sop-images \
 *     [--login-selector-user '#username'] [--login-selector-pass '#password'] \
 *     [--login-selector-submit 'button[type=submit]'] \
 *     [--nav-selector 'nav a'] \
 *     [--actions actions.json]
 *
 * 凭据传入方式(硬规则,不可绕过):
 *   优先从环境变量 SOP_USER / SOP_PASS 读取。--user/--pass 命令行参数仍被兼容解析,
 *   但**不推荐**——argv 会落进 shell history、`ps aux` 可见的进程列表、以及会话
 *   transcript/工具调用记录,即便脚本本身从不把凭据写进任何输出文件,这几处暴露
 *   面依然存在。调用方必须优先用环境变量方式调用本脚本。
 *
 * 依赖: playwright (npm install playwright 或已有全局安装)。
 * 缺失依赖时脚本会打印安装命令并退出,不擅自静默安装。
 *
 * 硬规则:
 *   - 凭据只用于本次登录动作,脚本不会把它们写进任何输出文件(截图/摘要 JSON/日志)。
 *     调用方同样不得把凭据写入产出文档。
 *   - 遍历不追随退出登录/注销类链接、外链、非 http(s) 协议链接,避免登录态被打掉后
 *     静默产出一批"错误截图"(见下方 isSkippableLink / isLoginRoute)。
 *
 * --actions <json文件> (可选,用于步骤 3 要求的"关键操作前/后两张截图"):
 *   [
 *     { "url": "https://.../export", "click": "button#export",
 *       "before": "export-before", "after": "export-after",
 *       "captureDownload": true }
 *   ]
 *   每条目:导航到 url(不填则用当前页)→ 等应用就绪(见下方"SPA 就绪等待") → 截 before 图 →
 *   click 选择器 → 等待网络空闲 → 截 after 图。产出存到 <out>/_actions/<name>-before.png / -after.png。
 *   这只覆盖"点一下按钮"这类简单副作用操作;更复杂的多步表单仍建议改走 MCP 手动截取。
 *   可选 captureBusyState:true —— 跳过点击后的就绪等待,直接截"刚点完"的瞬时忙态(如
 *   "导出中…"文案);默认(不填)点击后会等就绪(见下方"SPA 就绪等待")再截 after 图,
 *   拍到点击引发的新数据落定后的状态,而不是半成品。
 *   可选 captureDownload:true —— click 会触发浏览器下载时,同步捕获该下载事件,
 *   把文件存到 <out>/_actions/<name>-download.<ext> 并把 {name, suggestedFilename, sizeBytes}
 *   记进 <out>/_actions/_downloads.json,供调用方写"操作确有其效"的证据(文件名/字节数),
 *   而不必把整份业务数据截进图里。下载文件本身不含凭据,但可能含真实业务数据,写手册前自行判断是否入库。
 *
 * SPA 就绪等待(重要,踩过坑):hash 路由(如 #/reports/xxx)的页面内跳转不触发浏览器原生
 * 导航事件,goto 之后 domcontentloaded/networkidle 几乎立即通过——但页面数据是路由切换后
 * 才由前端 effect 发起 fetch 的,晚于这两个事件。只信 networkidle 会截到"加载中…"的半成品页面
 * (实测除首次真实整页加载外,后续所有 hash 内跳转的截图都会踩这个坑)。因此每次 goto 之后本脚本
 * 都会额外轮询等待页面自身的"加载中"文案消失(见 waitForAppReady),再截图。
 */

import fs from "node:fs";
import path from "node:path";

const LOGOUT_KEYWORDS = /logout|log-out|signout|sign-out|登出|注销|退出登录|退出系统/i;
const LOGIN_ROUTE_PATTERN = /\/(login|signin|sign-in|auth|sso)(\/|$|\?|#)/i;

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next && !next.startsWith("--")) {
        args[key] = next;
        i++;
      } else {
        args[key] = true;
      }
    }
  }
  return args;
}

function slugify(s) {
  return (
    s
      .toLowerCase()
      .replace(/^https?:\/\//, "")
      .replace(/[^a-z0-9一-龥]+/gi, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80) || "page"
  );
}

/**
 * 判断一个从导航栏收集到的 href 是否应当跳过遍历:
 *   - 空协议锚点(#)、mailto:、javascript: 等非页面链接
 *   - 非 http/https 协议
 *   - 跨域外链(遍历目标仅限被测系统自身)
 *   - 退出登录/注销类链接(命中即让整个 session 作废)
 * 返回 { skip: boolean, reason?: string }
 */
function isSkippableLink(href, linkText, baseOrigin) {
  if (!href || href === "#") {
    return { skip: true, reason: "锚点/空链接" };
  }
  if (href.startsWith("#")) {
    // hash 路由 SPA(如 #/reports/tier):是真实页面,不是锚点;纯 #section 锚点(无斜杠)仍跳过
    if (!href.startsWith("#/")) return { skip: true, reason: "页内锚点" };
    return { skip: false };
  }
  if (/^(mailto|javascript|tel):/i.test(href)) {
    return { skip: true, reason: "非页面协议" };
  }
  let resolved;
  try {
    resolved = new URL(href, baseOrigin);
  } catch {
    return { skip: true, reason: "无法解析的 URL" };
  }
  if (resolved.protocol !== "http:" && resolved.protocol !== "https:") {
    return { skip: true, reason: `协议不在白名单: ${resolved.protocol}` };
  }
  if (resolved.origin !== baseOrigin) {
    return { skip: true, reason: `跨域外链: ${resolved.origin}` };
  }
  const haystack = `${href} ${linkText || ""}`;
  if (LOGOUT_KEYWORDS.test(haystack)) {
    return { skip: true, reason: "疑似退出登录/注销链接" };
  }
  return { skip: false };
}

function isLoginRoute(urlStr) {
  try {
    const u = new URL(urlStr);
    return LOGIN_ROUTE_PATTERN.test(u.pathname + u.search + u.hash);
  } catch {
    return false;
  }
}

/**
 * hash 路由 SPA 的"就绪等待":goto 之后 networkidle 几乎立即通过(客户端路由跳转不算浏览器
 * 原生导航),但页面数据是路由切换后才由前端 effect 发起 fetch 的。轮询等待"加载中"文案消失,
 * 超时也不抛错(不是所有页面都有这个文案,或者该页面确实一直在读缓慢查询)——调用方结合截图
 * 人工判断,脚本只负责把等待做到位,不因此判失败。
 */
async function waitForAppReady(page, { timeoutMs = 15000, loadingTexts = ["Loading", "加载中"] } = {}) {
  // 先小睡一下再开始轮询:hash 内跳转后新路由的"加载中"文案往往要等一拍才渲染出来,
  // 不等这一拍会在文案出现前就误判"已就绪",真正等到的只是本函数末尾那固定的 400ms。
  await page.waitForTimeout(300);
  try {
    await page.waitForFunction(
      (texts) => !texts.some((t) => document.body.innerText.includes(t)),
      loadingTexts,
      { timeout: timeoutMs },
    );
  } catch {
    // 超时:继续走,截图仍然拍,但可能拍到未加载完的状态——留给人工核对。
  }
  // 数据到位到图表/表格完成绘制通常还有一小段渲染时间,留一点余量。
  await page.waitForTimeout(400);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.url || typeof args.url !== "string") {
    console.error(
      "用法: SOP_USER=<用户名> SOP_PASS=<密码> node crawl.mjs --url <部署URL> --out <截图输出目录>",
    );
    process.exit(1);
  }

  let chromium;
  try {
    ({ chromium } = await import("playwright"));
  } catch (e) {
    console.error(
      "[sop-generate] 未找到 playwright,请先运行: npm install playwright && npx playwright install chromium",
    );
    process.exit(1);
  }

  const outDir = path.resolve(args.out || "docs/sop-images");
  fs.mkdirSync(outDir, { recursive: true });

  const baseOrigin = new URL(args.url).origin;

  // 凭据:优先环境变量,--user/--pass 兼容但不推荐(见文件头注释)
  const user = process.env.SOP_USER || args.user;
  const pass = process.env.SOP_PASS || args.pass;
  if (args.user || args.pass) {
    console.warn(
      "[sop-generate] 检测到 --user/--pass 命令行参数:不推荐,凭据会落进 shell history 与进程列表。" +
        "请改用 SOP_USER/SOP_PASS 环境变量调用本脚本。",
    );
  }

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log(`[sop-generate] 打开 ${args.url}`);
  await page.goto(args.url, { waitUntil: "domcontentloaded" });

  // --- 登录段(可选,提供账号密码时执行) ---
  let loggedIn = false;
  if (user && pass) {
    const userSel =
      args["login-selector-user"] || 'input[name="username"], input[type="email"], #username, input[type="text"]';
    const passSel =
      args["login-selector-pass"] || 'input[name="password"], input[type="password"], #password';
    const submitSel = args["login-selector-submit"] || 'button[type="submit"], input[type="submit"]';
    try {
      await page.fill(userSel, user);
      await page.fill(passSel, pass);
      await page.click(submitSel);
      await page.waitForLoadState("networkidle").catch(() => {});
      loggedIn = !isLoginRoute(page.url());
      if (loggedIn) {
        console.log("[sop-generate] 登录动作已执行(账号密码不会写入任何输出文件)");
      } else {
        console.warn(
          "[sop-generate] 登录提交后仍停留在登录态路由,登录可能未成功。继续遍历,但页面很可能是登录页——请检查 --login-selector-* 是否匹配。",
        );
      }
    } catch (e) {
      console.warn(
        `[sop-generate] 登录选择器未命中(${e.message})。请用 --login-selector-* 参数指定实际选择器,或改用 playwright-mcp 手动登录后再遍历。`,
      );
    }
  } else {
    console.log(
      "[sop-generate] 未提供凭据(SOP_USER/SOP_PASS),跳过登录段(适用于无需登录的页面,或已用 MCP 手动登录)",
    );
  }

  // --- 遍历段:从导航结构收集页面链接,过滤退出登录/外链/非法协议 ---
  const navSel = args["nav-selector"] || "nav a, header a, aside a";
  const rawLinks = await page.$$eval(navSel, (els) =>
    els.map((el) => ({ href: el.getAttribute("href"), text: (el.textContent || "").trim() })),
  );

  const seen = new Set();
  const links = [];
  const skipped = [];
  for (const { href, text } of rawLinks) {
    if (!href || seen.has(href)) continue;
    seen.add(href);
    const verdict = isSkippableLink(href, text, baseOrigin);
    if (verdict.skip) {
      skipped.push(`${href} (${verdict.reason})`);
    } else {
      links.push(href);
    }
  }
  console.log(`[sop-generate] 从导航发现 ${links.length} 个可遍历链接: ${links.join(", ")}`);
  if (skipped.length > 0) {
    console.log(`[sop-generate] 已过滤跳过 ${skipped.length} 个链接:\n  ${skipped.join("\n  ")}`);
  }

  const summary = [];
  // 落地页自身必须在采集范围内(去重后置于首位),否则导航有链接时首页会被跳过。
  // 用规范化后的 href(而非原始 args.url)做基准:URL 会补全尾斜杠等,若两处不一致,
  // 首页会被 slugify 成 "app-example" 而不是 "home"(见下方 slug 判断)。
  const landingHref = new URL(args.url).href;
  const pagesToVisit = [...new Set([landingHref, ...links])];

  for (const link of pagesToVisit) {
    const target = link.startsWith("http") ? link : new URL(link, args.url).toString();
    const slug = slugify(link === landingHref ? "home" : link);
    const pageDir = path.join(outDir, slug);
    fs.mkdirSync(pageDir, { recursive: true });

    try {
      await page.goto(target, { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle").catch(() => {});
      await waitForAppReady(page);

      // 登录态校验:若中途被弹回登录页,session 已作废,后续截图全是登录页——立即中止
      if (user && pass && loggedIn && isLoginRoute(page.url())) {
        console.error(
          `[sop-generate] 访问 ${target} 后落回登录态路由(${page.url()}),session 可能已失效。中止遍历,已采集页面见 _index.json。`,
        );
        break;
      }

      // 截图存盘
      const screenshotPath = path.join(pageDir, "full.png");
      await page.screenshot({ path: screenshotPath, fullPage: true });

      // accessibility 摘要(不含整页截图内容,供调用方写文案用)
      // page.accessibility 在新版 Playwright 已移除;ariaSnapshot(v1.44+)是官方替代
      const snapshot = await page.locator("body").ariaSnapshot();
      const interactive = await page.$$eval(
        "a, button, input, select, textarea, [role=button]",
        (els) =>
          els.slice(0, 200).map((el) => ({
            tag: el.tagName.toLowerCase(),
            role: el.getAttribute("role") || undefined,
            text: (el.textContent || el.getAttribute("placeholder") || el.getAttribute("aria-label") || "")
              .trim()
              .slice(0, 60),
          })),
      );

      const pageSummary = {
        url: target,
        slug,
        title: await page.title(),
        screenshot: path.relative(process.cwd(), screenshotPath),
        interactiveElements: interactive,
      };
      fs.writeFileSync(
        path.join(pageDir, "summary.json"),
        JSON.stringify(pageSummary, null, 2),
        "utf-8",
      );
      summary.push(pageSummary);
      console.log(`[sop-generate] 已采集: ${target} -> ${pageDir}`);
    } catch (e) {
      console.warn(`[sop-generate] 页面采集失败,跳过: ${target} (${e.message})`);
    }
  }

  fs.writeFileSync(path.join(outDir, "_index.json"), JSON.stringify(summary, null, 2), "utf-8");
  console.log(`[sop-generate] 完成,页面清单见 ${path.join(outDir, "_index.json")}`);

  // --- 可选段:关键操作前/后截图(--actions <json文件>) ---
  if (args.actions) {
    const actionsPath = path.resolve(String(args.actions));
    let actionList = [];
    try {
      actionList = JSON.parse(fs.readFileSync(actionsPath, "utf-8"));
    } catch (e) {
      console.warn(`[sop-generate] 读取 --actions 文件失败,跳过该段: ${e.message}`);
      actionList = [];
    }
    if (actionList.length > 0) {
      const actionsDir = path.join(outDir, "_actions");
      fs.mkdirSync(actionsDir, { recursive: true });
      const downloads = [];
      for (const action of actionList) {
        const name = action.name || slugify(action.click || action.url || "action");
        try {
          if (action.url) {
            await page.goto(action.url, { waitUntil: "domcontentloaded" });
            await page.waitForLoadState("networkidle").catch(() => {});
            await waitForAppReady(page);
          }
          if (user && pass && isLoginRoute(page.url())) {
            console.warn(`[sop-generate] 动作 ${name} 前置导航落回登录页,跳过该动作。`);
            continue;
          }
          const beforePath = path.join(actionsDir, `${name}-${action.before || "before"}.png`);
          await page.screenshot({ path: beforePath, fullPage: true });
          if (action.click) {
            if (action.captureDownload) {
              const [download] = await Promise.all([
                page.waitForEvent("download"),
                page.click(action.click),
              ]);
              const suggested = download.suggestedFilename();
              const ext = path.extname(suggested) || "";
              const downloadPath = path.join(actionsDir, `${name}-download${ext}`);
              await download.saveAs(downloadPath);
              const sizeBytes = fs.statSync(downloadPath).size;
              downloads.push({ name, suggestedFilename: suggested, sizeBytes, savedTo: path.relative(process.cwd(), downloadPath) });
              console.log(`[sop-generate] 捕获下载: ${name} -> ${suggested} (${sizeBytes} bytes)`);
            } else {
              await page.click(action.click);
            }
            await page.waitForLoadState("networkidle").catch(() => {});
            // 点击本身也可能触发新的异步数据请求(如切换品牌口径重新拉数),同样会先拍到
            // "加载中…"半成品——除非调用方明确要抓转瞬即逝的忙态(见 captureBusyState),
            // 否则默认再等一轮就绪,拍到点击后真正落定的状态。
            if (!action.captureBusyState) await waitForAppReady(page);
          }
          const afterPath = path.join(actionsDir, `${name}-${action.after || "after"}.png`);
          await page.screenshot({ path: afterPath, fullPage: true });
          console.log(`[sop-generate] 动作截图完成: ${name} -> ${beforePath}, ${afterPath}`);
        } catch (e) {
          console.warn(`[sop-generate] 动作 ${name} 执行失败,跳过: ${e.message}`);
        }
      }
      if (downloads.length > 0) {
        fs.writeFileSync(
          path.join(actionsDir, "_downloads.json"),
          JSON.stringify(downloads, null, 2),
          "utf-8",
        );
      }
    }
  }

  await browser.close();
}

main().catch((e) => {
  console.error("[sop-generate] 脚本执行失败:", e);
  process.exit(1);
});
