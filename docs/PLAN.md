# claude-workflow-kit — 路线图

> 本仓是**开源插件市场仓**,不是业务项目:没有 BUSINESS/DEPLOYMENT 这类文档,进度只用本文件 + `Progress.md` 两件套。
> 分发形态见 README;内部版(stellark / huake)的对应关系与不开源边界另见各自仓库,**内部实名不进本仓**。

## 当前状态

- 最新发布:**v2026.08.13**(首个 tag 与 GitHub Release)
- 插件版本:workflow / workflow-en `0.9.0` · workflow-codex `0.9.0` · ui-sweep / ui-sweep-en `0.2.0` · send-to / send-to-en `0.4.1` · speak-human `0.4.1` / speak-human-en `0.3.1`

## Phase 路线

### Phase 1 — 方法论固化 ✅

工作流 prompt(三层分工 / 档位表 / 升降档原则 / 主流程)+ `/scaffold` 铺 docs 八件套 + `/whats-next` 续航导航 + `/sop-generate`;中英双插件 + Codex CLI 移植版。

### Phase 2 — 说话与协作纪律 ✅

`speak-human`(提问自检清单 P1~P9 + 表达纪律 S1~S4,带 evals)· `send-to`(跨会话消息转达)· auto-scaffold 常驻能力。

### Phase 3 — 防漏机制 ✅(2026-08-13)

三条机制补上"做完了但漏掉"的三类缺口:

- **目标台账** — 需求当轮落账,治「说过的需求做着做着就忘了」;
- **组件索引闭环** — 调研内部先行(查)+ 收尾登记(造)+ 定期校对(兜底);
- **UI 回归网** — `ui-sweep` 插件 + 接进主流程三入口。

外加四条评审纪律(链式对抗评审 / 评审报差异 / 安全加固措辞 / 生产红线前置),来自 190 场真实会话语料的反向学习。

### Phase 4 — 待定

下一个 Phase 尚未规划。候选方向见 `Progress.md` 的「待办」一节;开新 Phase 走 brainstorming → spec → ultracode。

## Spec 索引

- [分支即推与 main 门禁](superpowers/specs/2026-08-03-branch-push-policy-design.md) — 日常分支即推;2026-08-31 起并入默认分支只对前端可见改动设确认点,其余直接合并
- [业务档案文档](superpowers/specs/2026-08-03-business-doc-design.md) — docs 八件套加入 BUSINESS.md 与 7 格业务追问
- [新项目自动铺设](superpowers/specs/2026-08-11-auto-scaffold-design.md) — auto-scaffold 常驻判定规则与 evals
- [send-to 直发标准化与身份注册](superpowers/specs/2026-08-12-send-to-socket-registry-design.md) — uds 直发升标准路径 + 会话身份注册表
- [senior 四点纪律](superpowers/specs/2026-08-12-senior-four-improvements-design.md) — 链式对抗评审 / 报差异 / 安全措辞 / 红线前置
- [目标台账](superpowers/specs/2026-08-13-goal-ledger-design.md) — REQUIREMENTS 收件箱节 + 三对账点 + /goal 粘合
- [ui-sweep UI 全量交互遍历](superpowers/specs/2026-08-13-ui-sweep-design.md) — agent-browser 驱动 + 通用化遍历引擎
- [ui-sweep 孤儿功能对账](superpowers/specs/2026-08-13-ui-sweep-orphan-check-design.md) — 代码清单 vs 遍历实际到达求差集
- [docs-capture 决策/文档采集三层 hook](superpowers/specs/2026-08-14-docs-capture-hooks-design.md) — AskUserQuestion 拍板自动记入 inbox + 信号词软提醒 + commit 门禁催消化;四面已交付(kit wip 分支 / dev-toolkit 1.3.0 wip / claude-toolkit-engineer 0.15.0 wip / 本机 settings.json,三仓待 Tony 门禁并 main)
