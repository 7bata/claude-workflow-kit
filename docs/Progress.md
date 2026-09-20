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
