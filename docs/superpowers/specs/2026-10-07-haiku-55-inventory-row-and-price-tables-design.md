# Haiku 5.5 发布后的跟进:盘点行改 haiku 首选 + 三处模型价格表补行(2026-10-07)

## 背景

Haiku 5.5 于 2026-10-07 发布:ID `claude-haiku-5-5`,1M 上下文、128K 输出,支持 effort 五档(默认 medium;4.5 不接收 effort),价格按提示长度分两档(≤100K:$0.10 / $0.50;>100K:$0.50 / $2.50;4.5 是 $1 / $5),分词器同 4.7 之后的模型(同样文本多约 30% token)。本机 Claude Code 2.1.292 的 `haiku` 别名实测仍解析到 Haiku 4.5(冒烟子代理转录 model 为 claude-haiku-4-5-20251001);2.1.293 的编译模型目录把 `haiku` 指向 5.5(升级后 `claude -p --model haiku` 实测 modelUsage 为 claude-haiku-5-5)。

## 目标覆盖声明

覆盖目标清单 2026-10-07 条「haiku 5.5发布了,你看一下需不需要更新」里 Tony 选定的三项:

1. 升级 Claude Code 到 2.1.293 并复验 `haiku` 别名(主对话已做)。
2. 档位表「定位文件 / 列清单 / 盘点」行改成 `haiku` 首选,同步各副本(主对话已做,待评审)。
3. stella3 与 kpi-measure 的模型价格表补 Opus 5.5 / Haiku 5.5 行(stella 生产仓由主对话 cherry-pick 同一提交到 wip 分支,是否并 main 等 Tony 定)。

明确不覆盖:「批量机械执行」行的 haiku 对照实验(Tony 未选,行保持 `sonnet`);Haiku 5.5 >100K 的分层计价逻辑(两张表都是平价表,只填低档并注明);hapi 里「haiku is 200k」只是注释,不改;dev-toolkit-engineer 仓 2026-08-13 已封存,不同步。

## 单元

### U1 档位表盘点行(主对话已改,待评审)

九处副本:本机全局 CLAUDE.md(行 + 派工句 + 一段说明)、kit README 中英(行 + 派工句 + 一段说明)、kit workflow / workflow-en 脚手架模板(行)、内部工具包 WORKFLOW.md(同全局)、stellark-workflow 核心 SKILL.md(行压成「`haiku`,败则 `sonnet`」,派工句压成 'haiku'/'sonnet';字数基线 6499.57,不许增加)、stellark-parallel-do SKILL.md(行)、stellark-scaffold 模板(行)。upstream-map.md 记下核心的两处压缩。kit workflow / workflow-en 版本 0.18.0 → 0.18.1。

验收:九处的行都表达「haiku 首选、出错才换 sonnet」(核心用「败则 sonnet」的压缩写法);「便宜 20 倍」要注明只在提示 ≤100K 档成立;核心字数 ≤ 6499.57,「不许 / 禁止 / 必须 / 一律」与 `references/` 出现次数不变;中英措辞一致;说明段写明 2.1.293 起别名才到 5.5、更早版本写完整型号。

### U2 stella3 用量成本表(sonnet medium,TDD)

文件:`backend/internal/service/agentwatch/project_usage_cost.go` 与同目录 `_test.go`(工作树 `.worktrees/wip-price-table-haiku55`,分支 `wip/price-table-haiku55`,基于 origin/main 9083bc7f)。

- `modelPrices` 加两档:`"opus-5-5": {In: 4.00, Out: 20.00, CacheWrite: 5.00, CacheRead: 0.20}`、`"haiku-5-5": {In: 0.10, Out: 0.50, CacheWrite: 0.125, CacheRead: 0.01}`。
- `modelKeyPatterns` 里 `{"opus-5-5", "opus-5-5"}` 排在 `{"opus-5", "opus-5"}` 之前,`{"haiku-5-5", "haiku-5-5"}` 排在 `{"haiku", "haiku"}` 之前。
- 注释:定价快照日期改 2026-10-07;Opus 5.5 缓存读是输入价的 5%(官方特批,不套 0.1);Haiku 5.5 按 ≤100K 档填,>100K 实价是 5 倍,表里不分层。
- 测试:`TestModelUnitPrice` 加 `claude-opus-5-5` → opus-5-5、`claude-haiku-5-5` → haiku-5-5,并保留 `claude-opus-5` → opus-5、`claude-haiku-4-5` → haiku 的回归;加一个成本折算用例(haiku-5-5 1M 输入 = $0.10)。
- 验收:`go test ./internal/service/agentwatch/ -count=1` 通过;`go vet` 通过。

### U3 kpi-measure 价格表(sonnet medium,TDD)

文件:根目录 `pricing.json`(真源)、`cmd/kpi/pricing.json`(`go generate ./cmd/kpi` 生成的内嵌副本)、`internal/pricing/pricing_test.go`(分支 `wip/price-table-haiku55`,主检出)。

- 加行(updated_at 2026-10-07):`claude-opus-5-5` 4 / 20 / 5 / 0.2;`claude-sonnet-5-5` 2 / 10 / 2.5 / 0.2;`claude-haiku-5-5` 0.1 / 0.5 / 0.125 / 0.01;`claude-fable-5-1` 10 / 50 / 12.5 / 0.25。
- 改行:`claude-sonnet-5` 自 2026-09-01 起那行由 3 / 15 / 3.75 / 0.3 改为 2 / 10 / 2.5 / 0.2(官方 2026-10-07 定价页脚注:原定 9 月 1 日涨价取消,$2 / $10 为标准价),updated_at 改 2026-10-07。
- 测试:加用例装载根目录真实 `pricing.json`,断言 `claude-haiku-5-5`、`claude-opus-5-5`、`claude-sonnet-5-5`、`claude-fable-5-1` 各命中新行,`claude-opus-5-5-20261007` 这类带后缀的也命中 5-5 行,`claude-sonnet-5` 在 2026-09-01 之后是 $2 / $10;加一个断言两份 pricing.json 字节相同。
- 验收:`go generate ./cmd/kpi` 后 `go test ./... -count=1` 通过;`go vet ./...` 通过。

## 容易漏的输入与失败情形

1. stella3 的子串匹配顺序:`opus-5` 会命中 `claude-opus-5-5`,`haiku` 会命中 `claude-haiku-5-5`,新规则必须排在旧规则前(U2 测试覆盖)。
2. kpi-measure 带日期后缀的模型 ID(如 `claude-opus-5-5-20261007`)按最长前缀应命中 5-5 行,不是 opus-5 行(U3 测试覆盖)。
3. kpi-measure 内嵌副本与根目录不一致时 CLI 用的是旧价(U3 测试断言两份相同)。
4. 官方定价页里 Sonnet 5.5 的缓存读在模型表写 $0.20、在缓存一节写 $0.10,两处不一致;本次按模型表取 $0.20(U3 注释注明)。
5. Haiku 5.5 提示超过 100K token 时两张表都偏低 5 倍(本次明确不覆盖,注释注明)。

## 评审

U1:盲审 2 个 `opus` + `medium`,镜头是九处副本一致性 / 核心字数与禁令词 / 中英措辞;U2、U3:盲审各 2 个 `opus` + `medium`,镜头是正确性与边界(匹配顺序、前缀)、测试覆盖。有 P0/P1 修后裁决(`opus` + `high`)。链记录:`docs/reviews/2026-10-07-haiku55-chain.md`。
