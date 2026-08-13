# Progress

## 进度总览

| 模块 | 状态 | 备注 |
|---|---|---|
| workflow / workflow-en(方法论 prompt + scaffold/whats-next/sop-generate) | done | 0.7.0;含目标台账、四点评审纪律、调研内部先行、组件索引三入口 |
| workflow-codex(Codex CLI 移植版) | done | 0.6.0;无 hook 机制,auto-scaffold 靠手动 opt-in |
| speak-human / -en(提问与表达纪律 + evals) | done | 0.4.1 / 0.3.1;evals 34 条真实失败案例 |
| send-to / -en(跨会话消息 + 身份注册 hook) | done | 0.4.1;uds 直发为标准路径,四级阶梯 |
| ui-sweep / -en(UI 交互走查 + 孤儿对账) | done | 0.2.0;引擎 smoke 24 例,三入口接进主流程 |
| 进度文档层(PLAN/Progress) | done | 2026-08-13 补;此前只有 README + spec + git 历史 |

## 待办

| 事项 | 来源 | 优先级 |
|---|---|---|
| `speak-human` evals 声称 33 条(25 verified + 8 unverified),实际 `cases.jsonl` 为 34 条且无 verified 字段 | 2026-08-13 发布把关 | 低 |
| README 仓库结构树漏 `docs/` 与 `.agents/`;`speak-human-en` 标注「结构同 speak-human」但实际无 `evals/` | 2026-08-13 发布把关 | 低 |
| 内部版 CI 令牌 `dev-toolkit-ci-bot` **2027-04-20 到期**,到期后 auto-bump 会再次全红 | 2026-08-13 修 auto-bump 时建 | 到期前 |
| Phase 4 方向未定 | — | 待规划 |

## 变更日志(最新在上)

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
