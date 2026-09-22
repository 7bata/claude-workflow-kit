# Progress

## 进度总览

| 模块 | 状态 | 备注 |
|---|---|---|
| workflow / workflow-en(方法论 prompt + scaffold/whats-next/sop-generate) | done | 0.12.0;omitClaudeMd 机械 agent(agents/mechanical.md)、并发上限 env 文档;进度日志按月归档、评审轮次压进单元提交;需求先复述再动手、worktree 用完即删 + worktree-sweep hook;含目标台账、四点评审纪律、调研内部先行、组件索引三入口、docs-capture 三层 hook(kit/github 面)、main 门禁只拦前端可见改动、截图交付前视觉预审 |
| workflow-codex(Codex CLI 移植版) | done | 0.12.0;无 hook 机制,auto-scaffold 靠手动 opt-in;omitClaudeMd 判为 Claude 专有、并发对应 `[agents] max_threads` |
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

> 更早的日志按月在 docs/archive/Progress-YYYY-MM.md

### 2026-09-22 — 评审编排改为「盲审起步 + 接力续挖 + 裁决收尾」(workflow/-en/codex 0.13.0)+ Opus 5.5 换代评估

起因:Tony 说 Opus 已升到 5.5,问 workflow 的 prompt 哪里要改。核查:所有规则文本只用 `opus` 别名、无版本钉死,`claude -p --model opus` 实测已解析到 claude-opus-5-5,换代本身无需改 prompt;评估结论(三票 opus 反驳票核过)记在目标台账 2026-09-22 第一行,四条候选改法(规则 4 补"评审模型换代基线清零"与指标来源、前端派工 prompt 要点名要避开的样式、换代标注、effort 显式写的原因)待 Tony 拍板,未动手。顺带发现 9 月 7 日起两个项目的评审轮次 squash! 提交未 autosquash 就并进了 main(askthestalks 15 条、tools 57 条),dev-toolkit 的 stellark-workflow skill 缺规则 5,另案。

主体:Tony 先拍板"评审改成一个 agent 评审完、下一个带着前一个的问题继续挖,不投票",再问能否同时避开链式(锚定、首轮跑偏)与投票(重复、不能翻案、数票)各自的短板,选定方案 A——独立只用于发现、继承只用于深挖与翻案、全程不数票:首轮 2 个(规则 3 高风险单元 3 个)互不可见的盲审平行、镜头固定、统一 schema、脚本按 file+line 归并并标 conflict;之后每轮一个 agent 带前面各轮全部发现、先逐条推翻再找漏、换没用过的镜头;链末裁决轮 opus+high,盲审与续挖 medium;分流表(只有 P2 通过记遗留 / 只有 conflict 直接裁决 / P1 修后裁决 / P0 修后续挖再裁决)、上限 4 轮;修复不在评审 stage 里做,要修就结束本次运行、修完再开一次运行接原链,链状态落 scratchpad 文件;诊断/排障接力不设裁决轮。五处同步:全局 CLAUDE.md(四份为同一文件)、kit README zh/en + workflow/-en/codex 三份 scaffold 模板 + codex parallel-do §6、dev-toolkit(WORKFLOW.md、stellark-workflow 异构变体:盲审 opus ∥ 外部 CLI 包装 agent → 续挖 → fable 裁决,撤票改撤方、按链计上限;driving-codex、stellark-parallel-do、stellark-scaffold 模板、README、DECISIONS 新条目)、huake claude-toolkit-engineer 0.24.0 与 codex-toolkit-engineer 0.12.0(模板 + parallel-do + README 版本记录)。kit README 的 Codex 差异清单加一条"评审链档位与 Workflow 编排是 Claude 专有"。

评审:纯链式初版走了 4 轮链式接力(11+9+3+3 条发现,含 dev-toolkit 变体裁决轮归属、撤方规则、Codex 侧验收分工三处 P1);改成方案 A 后按新规则本身核:盲审 2 轮(一致性 / 可执行性,各 14 条)→ 脚本合并 → 续挖 1 轮(推翻 1 条定位、新增 6 条,含公开 README 混入内部例证)→ 修复 13 项 → 续挖第二轮(回滚与可逆性 / 对抗反驳)+ 裁决轮 opus high:裁决 reject,4 项 P1 必改(异构变体闭合定义、四份模板 xhigh 条把盲审镜头当续挖镜头、driving-codex 镜头句、全局 CLAUDE.md 无改前备份)全部修掉,并顺手修了 10 项 P2 中的 8 项(直通流程第 2 步区分 P1/P0、诊断链上限、链状态文件改放仓库内 docs/reviews/、file+line 归一化约定、Codex 主对话核出的问题并入、对外说明补「且无 conflict」、driving-codex 输出路径按单元分文件、README 1.1.0 历史行恢复原文);裁决轮建议修完自查不再开第 5 轮(已到 4 轮上限),按此办:grep 核对四项必改全部落实。遗留 P2:Codex 侧盲审 subagent 与主对话并发跑测试的端口/缓存冲突只写了约定未验证;driving-cwcode 的示例输出路径未核对。

回滚:全局 CLAUDE.md 改前版本备份在 `~/.claude/CLAUDE.md.bak-20260922-review-chain`(从本会话开场注入的原文恢复,与现版 diff 只差档位表两行、规则 2、直通流程第 2 步三处);五处同批回滚步骤见 dev-toolkit `docs/DECISIONS.md` 2026-09-22 条(四仓各 `git revert -m 1 <merge sha>`,手动管版本号的三个插件回滚时版本号继续往上加,全局文件从 .bak 恢复,再 `/plugin marketplace update`)。

### 2026-09-20 — 调研:jev-skill 要不要装进 kit(结论:不装、不融合,kit 无改动)

Tony 问给 workflow 加 jev-skill 有没有安装和融合的必要。jev-skill 是围绕 TypeSafe AI 的 Jev(2026-09-17 前后发布、只回答选择/打分/是非题的托管计费模型,尚在抢先体验并按排队放号)的一批第三方 skill 仓库,GitHub 同名搜索 43 个结果、40 个建于 9 月 16~20 日。结论:不装进 kit、不融合——kit 的判断点要么必须由脚本按固定规则判、要么依据是 Jev 拿不到也放不进 32k 输入上限的代码与对话、要么需要能照着改的具体意见而 Jev 只回分数;接入会让 hook 失去"不联网、不要密钥、出错静默放行",并把中文消息、提交标题、改动内容发到美国主机,与 huake 数据不出内网的前提冲突;唯一的 agent 对照试验(12 对)没看到变好且开销翻倍。`codaaiteam/jev-skill` 默认走第三方计费转发站,不建议装;想个人试用用官方 `typesafe-ai/skills`(附四个条件与卸载办法)。顺带结论:精简 skill 清单用 Claude Code 自带的 `/skills`(个人 skill)与 `/plugin`(插件 skill),不需要 Jev。报告 `docs/superpowers/research/2026-09-20-jev-skill-eval.md`(含 14 个判断点逐项对照、可检查的复查条件)。过程:三轮只读调研 8 个 sonnet 子代理 + 3 票 opus 评审(结论与适配 / 数据去向与依赖 high / 边界与异常情况),三票均判"结论成立需修改",推翻草稿三处(称无中文评测、`/skills` 建议对插件 skill 无效、官方 skill 不联网)并补 7 个漏掉的判断点与 `fast-jev-compaction`(5201 星)。

### 2026-09-19 — omitClaudeMd 机械 agent + 并发上限文档(workflow/-en 0.12.0)

起因:Claude Code 更新到 2.1.278(67 新功能等),Tony 让审 changelog 看 workflow 有无可加功能。挑出三项相关,Tony 圈定第 1/2/4,brainstorming 时又 YAGNI 掉 AGENTS.md(第 4 项),定为两项:①纯机械 stage(定位/清单;批量迁移/重命名/模板化)改用带 `omitClaudeMd: true` 的 `mechanical` 子代理类型(经 `agent(prompt,{agentType:'mechanical'})`),跳过自动加载的 CLAUDE.md、省 token,常规实现与全部评审照旧带 CLAUDE.md;②文档化 `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS`(1–256)并发上限旋钮,不改默认、只在机器有余量时调高,附 2026-09-19 过载事故告诫。冒烟验证 agentType+omitClaudeMd 生效(mech=NORULE、ctl=HASRULE)。镜像:本机全局 CLAUDE.md、kit README zh/en + workflow/-en 插件(新 `agents/mechanical.md`)、dev-toolkit(WORKFLOW.md + `plugins/dev-toolkit/agents/mechanical.md`)。huake 变体不在本机,待到 huake 侧镜像;workflow-codex 不涉(omitClaudeMd 为 Claude Code 专有)。同会话还诊断处理了 ccskip/HAPI hub 过载事故(32 个孤儿空转进程)、在 gitlab.stellark.io 建 StellarkAriel 群组 + Ariel 英文 Claude-facing onboarding;闲置会话自动回收器策略已定、实现仍 open(独立任务)。

### 2026-09-07 — 进度日志按月归档 + 评审轮次压进单元提交(0.11.0 / codex 0.11.0)

起因:Tony 贴来另一会话对 stella 八月代码量的审查,问「这是什么问题」。本会话在本机 stella 克隆上核对:审查的头号结论「27% 测试是重复脚手架」是行级去重把公共 helper 的调用当成复制粘贴(loginAndGetCookie 定义 1 处、调用 616 次;6 行块级重复测试 5~6%、源码 2%),不成立;站得住的是两个工作流问题——八月 docs 提交 241 条居各类之首、Progress.md 9,380 行 385 条日志(规则要求每次改代码都写日志,而 whats-next 只读最近 2~3 条),以及 fix 235 条里至少 77 条是评审某一轮各自成 commit(造成"三分之一在返工"的假象)。Tony 拍板两条对策。
- 规则 A「变更日志按月归档」:主文件只留当月,每月第一次批次收尾把上月及更早整体剪到 `docs/archive/Progress-<YYYY-MM>.md`,进度总览不归档,归档单独一个 `docs:` 提交;whats-next 读法加一句。
- 规则 B「评审轮次压进单元提交」:评审打回/复审/终验的修复用 `git commit --squash=<单元首个提交>`,并 main 前 `GIT_EDITOR=true git rebase --autosquash main` 压平再 `--force-with-lease` 推自己的 wip 分支(临时仓实测非交互可跑,轮次说明进提交正文;`--fixup=` 会丢说明故不用);main 禁止 force push 不变;已并 main 后的反馈修复仍独立 `fix:`;worktree-sweep 的祖先判定不受影响(`merge --squash` 会让它失效,故不采用)。副产品:压完后 `git log --format=%B | grep -c '^评审第'` 就是档位表规则 4 要的按单元打回率。
- 落点:本机全局 CLAUDE.md(§Git push 策略第 5 条 + 收尾句);kit README zh/en(§四 / §五.5 / §七.5 / §九.2)、workflow / workflow-en / workflow-codex 三套 scaffold 模板(§1 / 归档段 / §5.1.5 / 禁止事项两行)+ Progress.md.tmpl + whats-next;dev-toolkit(WORKFLOW.md、stellark-workflow、stellark-scaffold 模板、stellark-whats-next,f549aeb,CI 自动升版);huake claude-toolkit-engineer 0.23.0(30bd94c)/ codex-toolkit-engineer 0.11.0(8785cc9)。
- 编排:6 个 sonnet medium 实现单元,每单元两票 opus medium(完整性 / 副作用与格式)最多三轮,45 个 agent;三个单元一轮过,三个单元到第三轮只剩「拿不准」项,由主对话裁决:统一五面禁止事项措辞与顺序、codex 版第 5 条指代改清楚并删掉多出的第三行、codex Progress 模板头注改成与中文版同体例;顺手删掉 kit zh/codex whats-next 里历史遗留的重复「3. 随行注意」行(dev-toolkit/huake 本无此重复,范围外清理)。
- 本仓同批按规则 A 首次归档:8 月日志移入 `docs/archive/Progress-2026-08.md`(单独提交)。DECISIONS.inbox 两条 9 月 5 日旧草稿(已在目标清单)清空。
- 不覆盖:是否加「测试复用」规则(等档位校准数据);commit-gate 每次源码提交都要动 Progress.md 的频率;stella 仓现存 Progress.md 的实际归档由 stella 窗口按新规则自己做一次。

### 2026-09-05 — 需求先复述再动手 + worktree 用完即删 + worktree-sweep hook(0.10.0 / codex 0.10.7)

Tony 两条需求:①每次给出需求后 AI 先复述一句再动手(「收到,接下来做 X」);②最近 AI 建了很多 worktree 不自动清理。核查两周会话记录属实(88 次建、漏删全在 `.worktrees/` 之外、单项目残留近 800M),根因是 superpowers 收尾技能只清 `.worktrees/` 下的。规则层:全局 CLAUDE.md 新节「需求先复述再动手」与「Git push 策略」第 4 条「worktree 用完即删」;kit README zh 七之三 / 六之三 / §五.4 与 en 7c / 6c / 5.4;三份 scaffold 模板 §5.1 第 4 条、§7 复述 bullet、禁止事项两行、gitignore 模板 `.worktrees/`。自动化层:`worktree-sweep.sh` 挂 Stop + SessionEnd,五条判据全满足才 remove + branch -d + prune(已并 main、工作区干净、忽略文件里没有 .env/密钥/本地库/data/secrets 这类不可再生的、无会话或进程在用、30 分钟内没建没提交),已并但脏只提醒且一小时一次,冒烟测试 200+ 例含变异验证。评审四轮(opus high 安全票 + opus medium 测试票)先后修掉:set -f 让通配符会话根不展开、刚建的空 worktree 满足全部判据、忽略文件白名单只匹配根一级、data/ 子目录被折叠绕过、扫描命令失败被当成"没有"、node_modules 内的 data/ 路径误拦、C locale 下会话目录名算错、status 回写 index 污染新鲜度判据;忽略文件判定最终由主对话改为 ls-files 逐文件 + 依赖目录先剔除 + 黑名单正则。下游:dev-toolkit wip/worktree-hygiene-restate(59ff7f4,规则三处 + hook,CI 自动升版)、huake claude-toolkit-engineer 0.22.0(ef26ed1,模板 + hook)、codex-toolkit-engineer 0.10.5(062d9af,模板;engineer 版无目标清单故复述句去掉合成半句)。本机 hook 要等 dev-toolkit 插件更新后才生效(本机没装 kit 的 workflow 插件)。kit 本仓 7c575eb 按门禁(纯文档 + hook,前端不可见)直接并 main。

### 2026-09-01 — 撤回「跨天/批次做完即收尾换新会话」规则(0.9.6 / codex 0.10.6)

Tony 否决该规则:"每次新开窗口太麻烦了,不符合我的使用习惯"。全局 ~/.claude/CLAUDE.md 的对应节已删;kit 五处镜像(README zh/en 七之三 / 7c、workflow / workflow-en / workflow-codex 三份 scaffold 模板的 §7 条目与禁止事项行)同批撤除。0.9.5 / 0.10.5 批次里的另一项(启动模型钉版核查、fable[1m] 别名结论)不受影响,保留。原 kit 窗口已关,本批由家目录主窗口 tbata-92 代执行。

### 2026-09-01 — 跨天/批次做完即收尾换新会话写进规则(0.9.5 / codex 0.10.5);顺带核查启动模型钉版

Tony 的用量审计(经家目录主窗口 tbata-92 转达)发现跨天会话只占 3% 却消耗 58% 的 token、前 100 次大额缓存重建 98 次在跨天会话,全局 CLAUDE.md 新增「跨天会话阶段收尾即换新会话」。kit 五处同步:README zh/en 各加 七之三 / 7c 小节;workflow / workflow-en / workflow-codex 三份 scaffold 模板 §7 各加一条(写交接 recap 进 Progress 变更日志或 handoffs 目录、明确提醒用户开新会话、旧会话不再用"继续"推进),禁止事项加对应一行;codex 版改成 `~/.codex/handoffs` 与重开 `codex`,HAPI 细节不进 kit 面。同批核查"启动模型固定成最 SOTA":kit 仓没有 settings.json,README/模板只写"最强模型(如 Fable/Opus)"不钉版本,无需改;Claude Code 2.1.257 的 `--help` 与二进制别名表证实 settings 的 `model` 可写 `fable` / `fable[1m]` 自动跟最新版,本机全局与 labs/long/tech 三 profile 已是 `claude-fable-5-1[1m]`。

### 2026-09-01 — 门禁截图交付补"AI 先看一遍"预审步(0.9.4 / codex 0.10.4)

Tony 反馈门禁交付的截图里常有显而易见的问题,要求 AI(opus)先自己看一遍、觉得没问题再给他看。门禁"能"类分支在"散图不算"与"截不了图即停"之间插入预审句:交付前派视觉评审子代理(opus + medium;codex 版为自检措辞)逐张读图,专抓一眼可见的问题(布局错位、元素重叠、文字溢出/截断、乱码或占位文本、空白或缺数据区块、明显样式丢失、报错信息),查出先修复重截复审,通过才交付;拿不准是毛病还是有意设计的不硬修,交付正文点名让用户定并附一句评审结论。同步面:kit README zh/en 与三份模板(0.9.3→0.9.4,codex 0.10.3→0.10.4)、本机全局「截图交付规范」(补预审句)、dev-toolkit 六处副本(CI 自动升版)、huake claude 模板(0.21.3→0.21.4)与 codex 模板(0.10.2→0.10.4,顺带补上其漏掉的上一批"截不了图即停"句)。同日 Tony 拍板发 GitHub Release **v2026.09.01**(此前 tag 停在首发 v2026.08.13,五批改动只在 main):汇总门禁分流、截图 HTML 交付与预审、S4~S6、docs-capture,PLAN 发布行同步。
