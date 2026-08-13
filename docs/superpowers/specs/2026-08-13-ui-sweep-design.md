# ui-sweep:UI 全量交互遍历 skill — Design Spec

- 日期:2026-08-13
- 状态:已获 Tony 确认(形态=独立双语 bonus 插件 + 通用化引擎 + sop-generate 前置指引;铺面=kit + dev-toolkit + huake 全铺)
- 依据:stella 会话交接(2026-08-13)——调研 `docs/superpowers/research/2026-08-13-agent浏览器与UI遍历测试调研.md` 与实跑报告 `docs/reports/2026-08-13-UI全量交互遍历报告.md`(均在 stella 仓 wip/ui-sweep-sop;本机导出副本与抢救的脚本在会话 scratchpad `ui-sweep-rescue/`)

## 1. 背景

Tony 拍板:SOP 截图前先把全站交互按钮系统性全点一遍;工具链调研定了 vercel-labs/agent-browser(★40.5k,Apache-2.0,AI 专用 Rust CLI,自带 Chrome,a11y 快照带元素引用)做驱动 + 自研 ~160 行遍历编排;stella 实跑 10 屏 220 击验证可行(0 异常,揪出 1 真缺陷)。现沉淀为可复用 skill。

## 2. 形态与交付物(kit 仓,本分支)

按 bonus 插件惯例(同 send-to/speak-human):

| 文件 | 内容 |
|---|---|
| `plugins/ui-sweep/skills/ui-sweep/SKILL.md` | 中文版流程(见 §4) |
| `plugins/ui-sweep/skills/ui-sweep/scripts/sweep.mjs` | 通用化遍历引擎(见 §3) |
| `plugins/ui-sweep/skills/ui-sweep/scripts/export-state.mjs` | 登录态导出工具(照搬抢救副本,路径参数化检查) |
| `plugins/ui-sweep/skills/ui-sweep/references/report-template.md` | 报告骨架:总量/真缺陷/假阳性定性/观察级/覆盖缺口(诚实记账)五节,照 stella 实跑报告结构 |
| `plugins/ui-sweep/.claude-plugin/plugin.json` | 0.1.0,描述含触发词与安全边界一句话 |
| `plugins/ui-sweep-en/…` | 英文版同构(SKILL/报告模板同义重译;两个 scripts 与 zh 逐字节一致) |
| `.claude-plugin/marketplace.json` | 登记 ui-sweep / ui-sweep-en 两条 |
| `README.zh-CN.md` / `README.md` | 「附赠插件:ui-sweep」节 + 目录树 |
| kit 三份 sop-generate SKILL.md(workflow / workflow-en / workflow-codex) | 各加一句前置指引:截图前建议先跑 ui-sweep 全量点一遍(en 同义;codex 版注明引擎是普通 node 脚本、Codex 侧同样可用) |

**frontmatter 纪律**:description/argument-hint 一律加引号(2026-08-12 静默丢弃教训),实现后跑严格 YAML 解析验证。

## 3. 引擎通用化(sweep.mjs,以抢救副本为基线)

实跑版是 stella 专属(ROOT/SCREENS/语言基线硬编码)。改造为「通用引擎 + 项目配置」:

1. **配置外置**:`node sweep.mjs <path>/sweep.config.mjs`,config 导出:`ROOT`(必填)、`SCREENS`(必填,`{id, path:[{css}|{text}], settleMs?}`)、`DENY_EXTRA`(可选正则,叠加默认拦截名单)、`ensureBaseline`(可选 async 钩子,替代 stella 的语言锁逻辑——语言/主题基线是项目相关的)、`OUT`(可选,默认 ./sweep-out)。缺必填项立即报错退出,不静默空跑。
2. **默认拦截名单保留**(吊销/解散/删除/退出/logout/revoke/归档/清除/重置/发送/保存/上传等中英正则),config 只能增补不能削减——安全底线不可配置弱化。
3. **指纹补 checkbox 勾选态**:现指纹 = url+元素数+文本长,盲区实证(在场共享开关未验证翻转);追加 `document.querySelectorAll('input:checked,[aria-checked="true"]').length`。
4. **`--strict` 模式**:每击必恢复现场(治"同屏状态累积掩盖后续点击变化"的假阳性,实跑中 Agents 设置三个按钮因此误判 dead);默认关(全量跑慢约一倍),SKILL.md 写明取舍与建议(初跑全量用默认,对 dead 清单复核时用 --strict 重点跑)。
5. 其余行为(六分类记账、重名取第 n、按名失配回落按位、prompt/confirm 一律驳回、45s 超时、JSONL 台账+每屏截图)与实跑版**等价保留**——它验证过,不做无实证的改动。
6. 两 scripts 过 `node --check`;写一个最小 config 解析冒烟(缺 ROOT 报错、合法 config 可加载——不依赖 agent-browser,不跑真实站点)。

## 4. SKILL.md(中文 canonical 结构;en 全文同义)

- frontmatter:name ui-sweep;description 含触发场景(SOP 截图前全量点一遍 / 改完一批 UI 做回归扫描 / "把所有按钮点一遍" / 交互冒烟);argument-hint `"[站点URL] [登录态说明,可选]"`。
- **环境要求**:`npm i -g agent-browser`(自带 Chrome for Testing,无 Playwright 依赖;Apache-2.0);版本参考 0.27.0 实测。
- **流程六步**:①依赖自检;②登录态注入(export-state.mjs 从真实浏览器 CDP 导出 cookies+localStorage 拼 storageState,`agent-browser state load` 吃——绝不碰口令明文,绝不把登录态文件入 git);③**屏清单编制**(唯一需要项目定制的部分:先开站点抓首屏快照,把每个"屏"= 从根 URL 出发的确定性恢复路径写进 sweep.config.mjs;SPA 的浮层/抽屉/页签各态算独立屏);④跑引擎(全量默认模式);⑤**结果判读**(六分类语义表 + 假阳性定性法:click-error 先查 dialog 台账——同步 prompt 堵塞是常客;dead 先想状态累积——用 --strict 复跑定性;当前态导航钮/被浮层盖住的副本判 dead 属正常;headless 下全屏/日期选择器 API 空转非产品问题);⑥按 references/report-template.md 产报告,真缺陷逐条真浏览器复核后才定罪。
- **安全边界(硬规则)**:破坏性按钮只记不点(默认名单+项目增补);confirm/prompt 一律驳回,不产生真实写入;`--allowed-domains` 圈死目标域;只扫自家或已获授权的站点;登录态文件用完即删。**[2026-08-13 实现期修订]**:实测证伪「旗标圈死」——它只限显式导航,点击驱动跳转拦不住、旧会话/预载登录态会使其失效;最终实现为双层防护:旗标(尽力而为)+ 引擎逐击域名校验(出域记 `left-domain` 并当场恢复现场),会话生命周期由引擎接管(隔离 `--session ui-sweep`,STATE_FILE 进 config 由引擎在受限会话内加载),分类由六类扩为八类。
- **已知局限**(诚实声明):checkbox 翻转仅指纹级验证;headless 环境部分浏览器 API 空转;canvas/自绘 UI 不在 a11y 快照里,本 skill 覆盖不到。
- **出处**:调研与实跑报告(stella 仓路径)、agent-browser 仓库、2026-08-13 实跑数据(10 屏 220 击,分类分布)。

## 5. merge 后铺面(不在本分支;各走 wip → Tony 门禁)

1. **dev-toolkit**(stellark):`plugins/dev-toolkit/skills/ui-sweep/` ← kit 中文版整目录;README 27→28 表加行;其 sop-generate 加同款指引;plugin.json 1.0.x → 1.1.0(加 skill 属 minor)+ description 提及。
2. **huake**(claude-toolkit-engineer):同上;⚠️ README 有「包含的 N 个 skill」计数,表格行与计数同步改;plugin.json 0.10.x → 0.11.0。
3. 本机个人 skills 目录(三 profile 软链)是否放副本:不放——个人面用 kit 插件本体即可,避免第四份血统(与 send-to 的裸 skill 历史包袱不同,新 skill 不再制造)。

## 6. 验收条款

1. 引擎:`node --check` 两 scripts 通过;config 冒烟通过;与抢救基线 diff 审阅——除 §3 点名的四处改造外行为等价,默认拦截名单一条不少且不可被 config 削减。
2. SKILL.md 双语逐节语义一致;frontmatter 严格 YAML 解析通过(全部新增 md);安全边界六条齐且语气不弱化。
3. plugin.json ×2 / marketplace.json 合法,`claude plugin validate` 通过。
4. 双语 README 节+目录树齐;三份 sop-generate 指引落位且既有内容零回归。
5. 乱码扫描零命中;en 与 zh 的 scripts 逐字节一致(md5)。

## 7. 实施与评审档位

- 分支 `wip/ui-sweep`,commit 即 push。
- ultracode:U1 引擎通用化+冒烟(sonnet/medium)∥ U2 SKILL.md zh(sonnet/medium)→ U3 en 重译(sonnet/medium)∥ U4 manifests+README+sop-generate 指引(sonnet/low);逐单元 opus/medium 评审(U1 镜头=与基线等价性+安全名单不可弱化;U2/U3=判读指南对实跑报告的忠实度),打回升 high。
- 终审 opus/high(开源门面+新插件+触碰三份既有 sop-generate)。
- merge 进 main 找 Tony 确认;随后铺面各走各的门禁。
