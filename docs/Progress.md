# Progress

## 进度总览

| 模块 | 状态 | 备注 |
|---|---|---|
| workflow / workflow-en(方法论 prompt + scaffold/whats-next/sop-generate) | done | 0.10.0;需求先复述再动手、worktree 用完即删 + worktree-sweep hook;含目标台账、四点评审纪律、调研内部先行、组件索引三入口、docs-capture 三层 hook(kit/github 面)、main 门禁只拦前端可见改动、截图交付前视觉预审 |
| workflow-codex(Codex CLI 移植版) | done | 0.10.7;无 hook 机制,auto-scaffold 靠手动 opt-in |
| speak-human / -en(提问与表达纪律 + evals) | done | 0.7.0 / 0.6.0;S1~S6(含 S6 更新日志式汇报);evals 43 条合成案例 |
| send-to / -en(跨会话消息 + 身份注册 hook) | done | 0.4.1;uds 直发为标准路径,四级阶梯 |
| ui-sweep / -en(UI 交互走查 + 孤儿对账) | done | 0.2.0;引擎 smoke 24 例,三入口接进主流程 |
| 进度文档层(PLAN/Progress) | done | 2026-08-13 补;此前只有 README + spec + git 历史 |

## 待办

| 事项 | 来源 | 优先级 |
|---|---|---|
| README 仓库结构树漏 `docs/` 与 `.agents/`;`speak-human-en` 标注「结构同 speak-human」但实际无 `evals/` | 2026-08-13 发布把关 | 低 |
| 内部版 CI 令牌 `dev-toolkit-ci-bot` **2027-04-20 到期**,到期后 auto-bump 会再次全红 | 2026-08-13 修 auto-bump 时建 | 到期前 |
| Phase 4 方向未定 | — | 待规划 |
| 本机 docs-capture 双重注册风险:dev-toolkit 1.3.0 插件版将来在本机拉取后,与 settings.json 直接注册二存一(dev-toolkit README 已写注意) | 2026-08-14 U6 评审 | 拉取插件版时 |
| docs-capture 英文词表召回窄(approve/ship/stick with 未覆盖,U2 评审记录),按宁漏勿错接受,待实际使用数据再扩 | 2026-08-14 U2 评审 | 低 |

## 变更日志(最新在上)

### 2026-09-05 — 需求先复述再动手 + worktree 用完即删 + worktree-sweep hook(0.10.0 / codex 0.10.7)

Tony 两条需求:①每次给出需求后 AI 先复述一句再动手(「收到,接下来做 X」);②最近 AI 建了很多 worktree 不自动清理。核查两周会话记录属实(88 次建、漏删全在 `.worktrees/` 之外、单项目残留近 800M),根因是 superpowers 收尾技能只清 `.worktrees/` 下的。规则层:全局 CLAUDE.md 新节「需求先复述再动手」与「Git push 策略」第 4 条「worktree 用完即删」;kit README zh 七之三 / 六之三 / §五.4 与 en 7c / 6c / 5.4;三份 scaffold 模板 §5.1 第 4 条、§7 复述 bullet、禁止事项两行、gitignore 模板 `.worktrees/`。自动化层:`worktree-sweep.sh` 挂 Stop + SessionEnd,五条判据全满足才 remove + branch -d + prune(已并 main、工作区干净、忽略文件里没有 .env/密钥/本地库/data/secrets 这类不可再生的、无会话或进程在用、30 分钟内没建没提交),已并但脏只提醒且一小时一次,冒烟测试 200+ 例含变异验证。评审四轮(opus high 安全票 + opus medium 测试票)先后修掉:set -f 让通配符会话根不展开、刚建的空 worktree 满足全部判据、忽略文件白名单只匹配根一级、data/ 子目录被折叠绕过、扫描命令失败被当成"没有"、node_modules 内的 data/ 路径误拦、C locale 下会话目录名算错、status 回写 index 污染新鲜度判据;忽略文件判定最终由主对话改为 ls-files 逐文件 + 依赖目录先剔除 + 黑名单正则。下游:dev-toolkit wip/worktree-hygiene-restate(59ff7f4,规则三处 + hook,CI 自动升版)、huake claude-toolkit-engineer 0.22.0(ef26ed1,模板 + hook)、codex-toolkit-engineer 0.10.5(062d9af,模板;engineer 版无目标清单故复述句去掉合成半句)。本机 hook 要等 dev-toolkit 插件更新后才生效(本机没装 kit 的 workflow 插件)。kit 本仓 7c575eb 按门禁(纯文档 + hook,前端不可见)直接并 main。

### 2026-09-01 — 撤回「跨天/批次做完即收尾换新会话」规则(0.9.6 / codex 0.10.6)

Tony 否决该规则:"每次新开窗口太麻烦了,不符合我的使用习惯"。全局 ~/.claude/CLAUDE.md 的对应节已删;kit 五处镜像(README zh/en 七之三 / 7c、workflow / workflow-en / workflow-codex 三份 scaffold 模板的 §7 条目与禁止事项行)同批撤除。0.9.5 / 0.10.5 批次里的另一项(启动模型钉版核查、fable[1m] 别名结论)不受影响,保留。原 kit 窗口已关,本批由家目录主窗口 tbata-92 代执行。

### 2026-09-01 — 跨天/批次做完即收尾换新会话写进规则(0.9.5 / codex 0.10.5);顺带核查启动模型钉版

Tony 的用量审计(经家目录主窗口 tbata-92 转达)发现跨天会话只占 3% 却消耗 58% 的 token、前 100 次大额缓存重建 98 次在跨天会话,全局 CLAUDE.md 新增「跨天会话阶段收尾即换新会话」。kit 五处同步:README zh/en 各加 七之三 / 7c 小节;workflow / workflow-en / workflow-codex 三份 scaffold 模板 §7 各加一条(写交接 recap 进 Progress 变更日志或 handoffs 目录、明确提醒用户开新会话、旧会话不再用"继续"推进),禁止事项加对应一行;codex 版改成 `~/.codex/handoffs` 与重开 `codex`,HAPI 细节不进 kit 面。同批核查"启动模型固定成最 SOTA":kit 仓没有 settings.json,README/模板只写"最强模型(如 Fable/Opus)"不钉版本,无需改;Claude Code 2.1.257 的 `--help` 与二进制别名表证实 settings 的 `model` 可写 `fable` / `fable[1m]` 自动跟最新版,本机全局与 labs/long/tech 三 profile 已是 `claude-fable-5-1[1m]`。

### 2026-09-01 — 门禁截图交付补"AI 先看一遍"预审步(0.9.4 / codex 0.10.4)

Tony 反馈门禁交付的截图里常有显而易见的问题,要求 AI(opus)先自己看一遍、觉得没问题再给他看。门禁"能"类分支在"散图不算"与"截不了图即停"之间插入预审句:交付前派视觉评审子代理(opus + medium;codex 版为自检措辞)逐张读图,专抓一眼可见的问题(布局错位、元素重叠、文字溢出/截断、乱码或占位文本、空白或缺数据区块、明显样式丢失、报错信息),查出先修复重截复审,通过才交付;拿不准是毛病还是有意设计的不硬修,交付正文点名让用户定并附一句评审结论。同步面:kit README zh/en 与三份模板(0.9.3→0.9.4,codex 0.10.3→0.10.4)、本机全局「截图交付规范」(补预审句)、dev-toolkit 六处副本(CI 自动升版)、huake claude 模板(0.21.3→0.21.4)与 codex 模板(0.10.2→0.10.4,顺带补上其漏掉的上一批"截不了图即停"句)。同日 Tony 拍板发 GitHub Release **v2026.09.01**(此前 tag 停在首发 v2026.08.13,五批改动只在 main):汇总门禁分流、截图 HTML 交付与预审、S4~S6、docs-capture,PLAN 发布行同步。

### 2026-08-31 — 生产线门禁分流 + 生产文档契约对齐 kit 八件套(dev-toolkit 批次)+ 门禁补"截不了图即停"句(0.9.3 / codex 0.10.3)

Tony 拍板生产线也按前端可见性分流、starter 文档契约分叉并轨。主体改动在 dev-toolkit 仓(c60360e,含 DECISIONS/Progress 记档):部署/提交技能全线分流(生产部署脚本 y/N 与回滚确认保留),新项目铺 kit 八件套、存量六件套由下游按 docs/PLAN.md 自适应,setup 的路径解析加固为落盘重读+失败即停。评审 2 opus high + 1 codex 异构首审,链式接力七轮收敛。评审新增的"起不了应用、截不了图时停止推送并报告门禁受阻,不许退化成纯文字确认"一句回灌到 kit README zh/en 与三份模板(0.9.2→0.9.3,codex 0.10.2→0.10.3)、huake 模板(0.21.3)与本机全局截图交付规范,防同源同步抹掉。已知限制:存量项目 skill 副本需另行下发批次(见目标台账 open 项)。


### 2026-08-31 — 截图交付改为合并单文件 HTML(0.9.2 / codex 0.10.2)

Tony 追加:给用户看的截图不再散发单张,一律合并成一个自包含 HTML(图片内嵌、浏览器直接打开、每图一行标题),发到会话界面供直接查看,并在正文写出可复制进浏览器的本地路径。门禁"能"类分支的交付要求改为此口径,十处副本同步;Tony 侧全局 CLAUDE.md 另立「截图交付规范」承载 HAPI 双路交付细节(hub 渲染 + TUI 路径),kit 面保持工具无关表述。

### 2026-08-31 — main 门禁补充:前端改动确认必须附页面(0.9.1 / codex 0.10.1)

Tony 追加要求:前端改动请求合并确认时,必须把改动后的页面贴出来供检查——截图或可直接打开的 HTML,光文字描述不算。写进 main 门禁"能"类分支,十一处副本同步;顺带补上早上批次漏掉的 codex-toolkit-engineer scaffold 模板(该份门禁与禁止事项当时仍是旧文,本批整条更新)。

### 2026-08-31 — speak-human 同步母本新增 S6「更新日志式汇报」(speak-human 0.7.0 / -en 0.6.0 / workflow-codex 0.10.0)

母本仓(5e4de8e)新增"说"的纪律第六条:进展/完成类汇报,做了两件以上独立的事、或有计划内没做成/已知问题要交代时,用「本次完成/未完成/已知问题」三段体——条目功能级零文件名、杂项归并、未完成各附一句原因、空段整段省略;单项且无未做无问题照 S4 一句结果不硬套。S4 形状表"一段进展汇报"行改分流、必留清单补"S6 未完成条目的原因句"。

- kit 面:zh / workflow-codex 内嵌两份条款区与母本逐字节同文,en 手译全套;evals 镜像同步(语料 +c41~c43 共 43 条、rubric S6 判分段与专项注记、run_evals.py S1~S6 与 S6 案例输出指令分支,保留 kit 侧 SKILL.md 路径差异);出处段按开源口径通用化。README zh/en 里 codex 版 speak-human 的"S1~S4"陈旧引用顺带更正为 S1~S6。
- 同步面:dev-toolkit、huake claude-toolkit-engineer(0.21.0,README 加记录行)、codex-toolkit-engineer(0.10.0)三仓 SKILL.md 同文同步;dev-toolkit 版本由 CI 自动升。

### 2026-08-31 — main 门禁改为只拦前端可见改动(workflow 三插件 0.8.0 → 0.9.0)

Tony 拍板:merge 进 main 按"用户在前端能不能看出/测出差别"分两类——能(前端代码改动,或后端逻辑变化改变前端交互/展示行为)必须先获用户确认;不能(纯后端内部实现与重构、文档、测试、脚本、CI、依赖升级、接口行为不变)直接合并并 push main,合并后报告一句。拿不准按"能"处理先问;本条覆盖 finishing-a-development-branch 等 skill 的"合并前一律询问"。

- 改动面:README zh/en §五/§5、workflow / workflow-en / workflow-codex 三份 scaffold 模板 §5.1(三插件版本 0.8.0 → 0.9.0;Progress 总览里 codex 旧标 0.6.0 为陈旧记录,实际改前已是 0.8.0)。两票 opus 评审(一致性/语义忠实度)后补修:五份模板「禁止事项」里"没确认不许并 main"同口径改为只禁前端可见改动(否则新规则在 scaffold 出的项目里被硬清单压掉,blocker);免问清单"测试"限定为"后端测试"(消除与前端测试改动的重叠);补"直接在 main 上 commit 仍先按规则 1 切分支";finishing-a-development-branch 覆盖声明点名到 Step 4 三选项菜单;PLAN.md 版本行与 spec 索引摘要同步。
- 同步面:本机全局 `~/.claude/CLAUDE.md`(即时生效)、stellark dev-toolkit(WORKFLOW.md + stellark-scaffold 模板 + stellark-portfolio 一句 + 三版本维护约定一句)、huake claude-toolkit-engineer(scaffold 模板,0.19.0 → 0.20.0);dev-toolkit-engineer 仓已封存不动。
- 未动待拍板:dev-toolkit 生产线技能(engineer 版 stellark-commit / stellark-deploy / starter CLAUDE.md)把并 main 确认与生产部署绑定,生产项目后端改动是否免确认直接部署,见 REQUIREMENTS 目标台账 open 项。

### 2026-08-14 — docs-capture 四面落地收口(U2~U6)+ 层 2 五轮定案

- **四面交付**:workflow-en 英文面(词表/判例全英文化+弯引号 U+2019 归一化)、stellark dev-toolkit 1.3.0(hooks.json 纯增段,凭据拦截逐字未动,opus/high 评审核过)、huake claude-toolkit-engineer 0.15.0(含 scaffold 模板同步)、本机 settings.json 注册(备份比对仅差新增三段)。三仓均 wip 分支已推,待门禁并 main。
- **层 2 词表五轮攻防定案**:两轮实现拟合失败 → 判例/实现分权 + 按子句切分处方 → 集外召回 22/22 满分但对抗性生活句误报触词表法天花板 → Tony 拍板"高召回软提醒":提示语自带免疫说明,验收标准改"领域内误报可忽略"入 spec。教训沉淀:启发式单元判例与实现第一轮就要分 agent 所有权,终审必做集外实测。
- 修复过程顺带收口:capture 多选含逗号 label 误判、commit-gate 词法位置匹配与 POSIX 化、branch upstream 错位(dev-toolkit wip 曾指向 origin/main,裸 push 可能绕过门禁)。

### 2026-08-14 — docs-capture 决策/文档采集三层 hook,kit(github)面(0.7.0 → 0.8.0)

治 stella 符合度审计发现的"写入侧零自动化"——DECISIONS/PLAN/Progress 全靠 Claude 自觉更新,失真会经 stella portfolio 每 10 分钟轮询自动扩散成对外错误。

- **层 1 确定性捕获**:`AskUserQuestion` 问答框拍板由 `PostToolUse` hook 逐字追加进 `docs/DECISIONS.inbox.md`,不摘要不判断,数据不丢。
- **层 2 信号提醒**:`UserPromptSubmit` hook 按决策词表/需求词表命中即软提醒,高召回设计(2026-08-14 五轮拍板改验收标准为「套内判例全绿 + 软件语境内误报可忽略」,不再追杀跳出软件语境的对抗句)。
- **层 3 commit 门禁**:`PreToolUse`(matcher: Bash 含 `git commit`)两项检查——inbox 有未消化草稿 / staged 含源码但未见 `docs/Progress.md` 更新;对 staged 内容取哈希,首警二放(同一份内容原样重跑即放行,不做"真的消化过"的语义校验)。
- `CLAUDE.md.tmpl` 文档同步规则表补一行 inbox 消化分流;`DECISIONS.md.tmpl` 头部如实改写为 inbox 流程说明(两语言)。
- 双语 README 加 docs-capture 节;`workflow-codex` 注明不移植(无 hooks 机制,纪律照旧靠约定)。
- **本次仅交付 kit(github)面**(spec §8 U1~U3);stellark dev-toolkit / huake claude-toolkit-engineer / 本机 `~/.claude/hooks` 三面并入见 spec §8 U4~U6,已登 Progress 待办与 REQUIREMENTS 台账。

### 2026-08-13 — 首次发布 v2026.08.13(tag + GitHub Release)

- **发布把关挡下一起阻断级事故**:`6f092f0`(组件索引三入口)分支点早于 `b33803a`(ui-sweep 三入口),合并**零冲突却静默回退**了后者 10 处入口(三份脚手架模板质检条、三面 whats-next 提示、双语 README 两段)。若照原样发布即"插件大力宣传、方法论里零调用入口"。已逐处恢复并与组件索引条目取并集。**教训**:分支点早于已合并分支时,合并必须逐文件核对基准,不能只看有没有冲突。
- **两轮脱敏**:首轮清内部项目名;把关发现 spec 里仍有内部主机名/仓名/绝对路径、`send-to` SKILL 正文含真实账号邮箱、双语 README 拿真实内部项目名当会话名示例 → 全部通用化,公开面实名扫描零命中。
- 版本与门面对齐:五个插件 bump、marketplace 四条描述、双语 README 补目标台账与孤儿对账、八分类括号补齐两类。

### 2026-08-13 — ui-sweep 孤儿功能对账(0.2.0)

代码清单 vs 遍历实际到达求差集,查「功能实现了但前端没入口 / 入口打不通」。**三轮复现级评审**(真 agent-browser + localhost 双端口 e2e),修掉的系统性误报源:屏 URL 不入账、`--clear` 位置错导致 mount 期 XHR 丢失、采集失灵与真零覆盖不可辨却谎称 full coverage、seenRoutes/seenApis 被第三方 XHR 污染、覆盖率分子分母不同源。顺带修存量安全漏洞:拦截名单只有中文破坏词,实测英文 `Delete item` 被真点、POST 真发出。

### 2026-08-13 — ui-sweep 接进主流程三入口

验收前扫描 / 项目硬规则质检条 / whats-next 补跑提示。**根因**:插件做完了但方法论正文零提及,抄了 prompt 的人不知道有这工具。复审补上闭环判据(走查记录须写明 `ui-sweep` 字样,0 缺陷也记),否则 whats-next 会常驻误报。

### 2026-08-13 — 目标台账 + 组件索引三入口 + 调研内部先行

- 目标台账:`REQUIREMENTS.md` 收件箱节 + 当轮登记硬规则 + 三对账点(brainstorming 开工 / 收尾销账 / whats-next 报未销账);`/goal` 管会话内跑偏,台账管跨批次蒸发。
- 组件索引:收尾登记 + 项目硬规则 + 季度校对;补上"只有消费侧回写、没有生产侧登记"的缺口。
- 调研规则补「第 0 步:内部先行」。

### 2026-08-13 — ui-sweep 插件从无到有(0.1.0)

`vercel-labs/agent-browser` 驱动 + 自研通用化遍历引擎,八分类记账 + 假阳性判读指南。三轮评审,复现级证伪「`--allowed-domains` 圈死目标域」(点击跳转拦不住),最终实现双层防护:旗标 + 引擎逐击域名校验当场拉回。

### 2026-08-12 — send-to 0.4.0 与 senior 四点纪律

- send-to:uds 直发从"最后手段"升为标准路径,新增会话身份注册 hook(解决"看得到 socket 认不出是谁"),四级阶梯 + 回声双档,全局停用开关。
- 四点纪律:链式对抗评审 / 评审报差异 / 安全加固措辞 / 生产红线前置到实现侧 prompt——来自 190 场真实会话语料的反向学习。
- frontmatter 严格 YAML 修复:`argument-hint` 与含裸冒号的 `description` 未加引号会被**静默丢弃整个 frontmatter**。
