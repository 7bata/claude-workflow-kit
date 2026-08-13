---
name: ui-sweep
description: "在 SOP 截图前把全站可交互元素系统性点一遍、改完一批 UI 后做回归扫描、用户说“把所有按钮点一遍”、或需要一次交互冒烟测试时触发。用 agent-browser 驱动 + 通用化遍历引擎,逐屏逐元素点击观察并六分类记账,产出 JSONL 台账、每屏截图与报告。"
argument-hint: "[站点URL] [登录态说明,可选]"
---

# ui-sweep — UI 全量交互遍历

SOP 截图前先把界面系统性点一遍,揪出「点了没反应」「点了报错」这类暗坑,再产 SOP 或回归验收——比人工肉眼过一遍快,比随机 monkey 测试有确定性覆盖保证。驱动是 [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser)(★40.5k,Apache-2.0,专为 AI agent 造的 Rust CLI:a11y 快照带元素引用、点击自带遮挡检测、`console`/`errors` 采集、confirm/prompt 显式接管、`state save/load` 登录态注入、`--allowed-domains` 域名圈禁),外加自研 ~220 行遍历编排(`scripts/sweep.mjs`)。2026-08-13 在 stella 项目实跑验证:10 屏 220 击,0 页面异常、0 console 报错,揪出 1 个真缺陷(看板「添加」空输入完全静默)。

## 环境要求

- `npm i -g agent-browser`——自带 Chrome for Testing,无 Playwright 依赖(Apache-2.0)。本 skill 按 0.27.0 实测(headless Chrome for Testing 152)编写,其他版本行为可能有出入。
- Node.js(跑 `scripts/sweep.mjs` 与 `scripts/export-state.mjs`);`scripts/export-state.mjs` 额外依赖 `playwright-core`(`scripts/package.json` 已声明,`npm i` 一次即可)。

## 流程六步

1. **依赖自检**:确认 `agent-browser --version` 能跑通;确认目标是自家或已获授权的站点(见下方安全边界)。
2. **登录态注入**:用 `scripts/export-state.mjs --cdp <CDP地址> --out <state.json> --origin <origin>...` 从一个已登录的真实浏览器(通过 CDP 连接)导出 cookies + 各 origin 的 localStorage,拼成 `{cookies, origins}` 结构;再用 `agent-browser state load <state.json>` 让遍历会话吃到同一份登录态。**绝不碰口令明文**(整个流程不涉及输入密码,只搬运已登录浏览器的态);**登录态文件用完即删,绝不把它入 git**。
3. **屏清单编制**(唯一需要项目定制的部分):先手动或用 `agent-browser open <ROOT>` + `snapshot -i` 抓首屏快照摸清结构,再把每个"屏"写进项目自己的 `sweep.config.mjs`。"屏" = 从 `ROOT` 出发的一条确定性恢复路径(`{id, path: [{css}|{text}], settleMs?}`,`path` 是从根到达该屏依次要点的元素);SPA 的浮层/抽屉/页签各种展开态,每个算一个独立屏,不要漏。
4. **跑引擎**:`node scripts/sweep.mjs <path>/sweep.config.mjs`。先跑一次 `--check-config` 确认 config 合法(缺 `ROOT`/`SCREENS` 会立即报错退出,不会静默空跑);全量遍历跑默认模式(不带 `--strict`,见下方取舍说明)。
5. **结果判读**:引擎把每次点击归到六类之一——`ok-changed`(指纹变化,含 checkbox 勾选态)、`dead`(无任何反应)、`dialog-dismissed`(弹窗被驳回)、`click-error`(点击命令本身出错)、`page-error`(页面抛未捕获异常)、`skipped-denylist`(命中拦截名单未点)。**假阳性定性法**(来自实跑复盘,先按这几条筛,再决定是否需要真浏览器复核):
   - `click-error` 先查 `dialog` 台账——同步 `window.prompt`/`confirm` 会堵塞点击命令直到超时,这类"报错"往往是按钮本身正常、只是弹窗同步阻塞;台账里能看到 prompt 内容和驳回记录即可排除。
   - `dead` 先想"同屏状态累积":引擎默认不追加恢复现场(见 `--strict` 说明),前序点击留下的展开态/提示可能掩盖了本次点击的效果,导致误判 dead——先用 `--strict` 对可疑 `dead` 清单重点复跑一次再下结论。
   - 当前态导航钮(已经在当前页的导航项)、被浮层盖住的报头/页面副本判 `dead` 属正常行为,不是缺陷。
   - headless 环境下全屏 API、原生日期选择器等浏览器 API 可能空转不生效,这是环境限制,不是产品问题。
   - 真缺陷(判定为产品问题的 `dead`/`click-error`/`page-error`)必须逐条用真浏览器手动复核坐实后才能定罪,不能只凭台账下结论。
6. **产报告**:照 `references/report-template.md` 的骨架产出——总量、真缺陷(已复核坐实)、假阳性定性(逐条说明排除依据)、观察级(不定罪但值得留意)、覆盖缺口(诚实记账哪些没点、为什么没点)五节。

## `--strict` 模式取舍

默认(不带 `--strict`):每屏内只在上一次点击改变了状态时才恢复现场,连续多次"无反应"的点击不重复恢复——跑得快(约为 `--strict` 的一半时间),代价是同屏状态可能累积掩盖后续点击的真实效果,产生上面提到的 `dead` 假阳性。

`--strict`:每次点击后无条件恢复现场(重新 `restore(screen)`)再点下一个——治状态累积假阳性,代价是全量跑慢约一倍。**建议**:初跑用默认模式覆盖全站,再对 `dead` 清单里可疑的条目用 `--strict` 重点复跑定性,不必对全站强制 `--strict`。

## 安全边界(硬规则)

- **破坏性按钮只记不点**:引擎内置默认拦截名单(吊销/解散/删除/退出/logout/sign out/revoke/归档/archive/清除/clear/重置/reset/发送/send/保存/save/上传/upload 等中英正则),命中的元素只记入台账(`skipped-denylist`),绝不点击。项目可以通过 `sweep.config.mjs` 的 `DENY_EXTRA`(正则)**叠加**拦截范围,但没有任何配置路径能削减或覆盖这份默认名单——安全底线不可配置弱化。
- **confirm/prompt 一律驳回**:每次点击后台账检查弹窗状态,只要检测到 `confirm`/`prompt`/`alert` 一律 `dismiss`,不产生真实写入。
- **`--allowed-domains` 圈死目标域**:遍历只在目标域内进行,不给引擎跑到目标域之外的机会。
- **只扫自家或已获授权的站点**:不对未获授权的第三方站点跑本 skill。
- **登录态文件用完即删**:`export-state.mjs` 产出的 state 文件含 cookies/localStorage,属敏感凭据,用完立即删除,绝不提交进 git、绝不上传。

## 已知局限(诚实声明)

- **checkbox 翻转仅指纹级验证**:指纹里补了 `input:checked`/`[aria-checked="true"]` 计数,能捕捉"勾选状态变了"的信号,但没有对每个 checkbox 的语义(勾上代表什么)做二次验证——不确定的场景仍建议人工复核一次。
- **headless 环境部分浏览器 API 空转**:全屏 API、原生日期/颜色选择器等在 headless Chrome 下可能不产生真实效果,对应的 `dead` 判定不代表产品缺陷。
- **canvas/自绘 UI 不在覆盖范围**:a11y 快照只认可被无障碍树感知的元素,canvas 画布或纯自绘(非标准 DOM 控件)的交互不会出现在遍历计划里,本 skill 覆盖不到,需要额外的专项验证。

## 出处

- 实跑数据:2026-08-13 stella 项目实跑,10 屏 220 击(ok-changed 106 / dead 97 / 拦截未点 11 / click-error 2 / 按位回落 2 / 定位丢失 2),0 页面异常、0 console 报错,揪出真缺陷 1 个(看板「添加」空输入完全静默)。
- 驱动:[vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser),0.27.0(headless Chrome for Testing 152)实测。
- 调研依据:内部工具链调研(GitHub 候选对比:agent-browser vs playwright-mcp/chrome-devtools-mcp(MCP 形态,全量遍历下 token/时延成本不成立)vs browser-use(非确定性)vs crawlee(URL 爬虫,SPA 屏内状态逻辑仍需自写)vs gremlins.js(随机 monkey 测试,已停维护))。
