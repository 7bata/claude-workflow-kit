# 评审链:加记裁决模型 + 内部工作流 skill 盲审去掉外部 CLI

spec:`docs/superpowers/specs/2026-10-03-adjudication-model-line-drop-external-cli-design.md`

单元:U1(本机全局规则 + 本仓中英 README 规则 4,提交 01dae87,主对话直接改)、U2(内部工具包,分支 `wip/drop-external-cli-adjudicator-model-line`,首个提交 ed9c191,实现模型 claude-sonnet-5-5)。都是规则文字单元,没有测试,对照实验不计入。机器 1 分钟负载 12 左右(10 核),全程顺序跑。

## 第 1 轮:盲审(2 个 opus + medium,互不可见,顺序跑)

| # | 位置 | 级别 | 发现 | 谁报的 |
|---|---|---|---|---|
| F1 | U2 `driving-codex/SKILL.md:40` 起 | P1 | 只改了 description 与开头一段;正文仍把 codex 写成评审链一方:小节「Prompting it as a chain round」、盲审 / 续挖镜头、effort 按链轮次取值、「codex never runs the verdict round」、不可用时换另一方顶位并记缺方(第 84~91 行)、末尾 chain rounds 与 cross-vendor 的说法。不符合 spec 3.2 与 AC2 | 两位都报 |
| F2 | U2 核心 `stellark-workflow/SKILL.md:36` | P1 | 档位表裁决轮行仍写「流程、撤方、链数上限见 references/review-chain.md」,而 review-chain.md 已没有撤方与链数上限(改成默认 4 轮) | 两位都报 |
| F3 | U2 核心 `SKILL.md:139` | P2 | `[^orch]` 脚注仍写「按链撤方」,是历史说明但读起来像现行规则 | 两位都报 |
| F4 | U2 `references/upstream-map.md:34` | P2 | 旧指针表一行仍写「裁决轮流程与撤方规则」 | 两位都报 |

两位都核对通过、没有发现的点:AC1(四个完整句的面与核心末句,英文与中文一致);AC3(核心 token 6532.0 → 6452.0;「不许」5 → 4 对应删掉的那一句,「禁止」8、「必须」6、「一律」15、`references/` 入口 13 不变);AC4(review-chain.md 保留 spec/plan 评审 (a)(b)(c)、测试资源卫生三条、分流、修复不在评审 stage 里做、4 轮上限);AC5(`claude plugin validate` 通过,只有原有的 hooks 引号警告);没有改到 spec 没让改的内容。U1 无发现。

合并:四条都是同一位置、同一级别,无 conflict。

分流:有 P1、无 P0 → 修复后跑裁决轮。修法:F1 按主对话给的逐段替换文本改正文(不再有链轮次、顶位、缺方的说法;不可用时告诉用户);F2 改成「流程、轮数上限见 references/review-chain.md」;F3 的脚注属保护段不动,F4 的左列是拆分前原文的引用也不动,两处都在 upstream-map.md 的本批记录里注明「撤方与链数上限已取消,这两处是历史说法」。

## 修复(评审链之外,机械子代理 sonnet + low 照主对话算好的 11 项精确替换套用)

内部工具包提交 aebd05d(压进 U2 的首个提交):`driving-codex/SKILL.md` 正文 9 处(小节改名为「Prompting it for a review」、去掉盲审 / 续挖镜头与链轮次、effort 改成默认 medium 与高风险或安全评审 high、不可用时告诉用户、末尾两句);核心 `SKILL.md:36` 改成「流程、轮数上限见 references/review-chain.md」;`upstream-map.md` 本批记录注明撤方与链数上限已取消、脚注与旧指针表里的说法是历史。核心 token 6452.0 → 6449.71。

## 第 2 轮:裁决(省略 model,实际运行在 claude-fable-5-1,high)

| # | 裁定 | 说明 |
|---|---|---|
| F1 | 闭合 | 正文已无链轮次、顶位、缺方、cross-vendor 的说法;命令形状、`-o` 读结果、模型与 effort 参数、账号池、反引号注意事项都还在,英文通顺 |
| F2 | 闭合 | 与 review-chain.md 的「默认上限 4 轮」对得上 |
| F3 | 闭合(记遗留) | 脚注是数据出处的历史叙述,对照表已注明;运行时读核心的人看不到这条注明,但现行规则处都已是 4 轮上限 |
| F4 | 闭合 | 左列是拆分前原文的引用,不改;同文件已注明 |

新发现(都是 P2,记遗留,不再开轮):
- 内部工具包 `README.md:164` 的 1.1.0 历史版本说明仍写「异构评审票」。
- 本仓英文 `README.md:222` 新句用 adjudication round,同文件其余处都叫 verdict round(用词出自 spec 原文)。
- 「裁决模型」行只记裁决轮:盲审直接判通过的单元没有这一行,盲审与续挖的 opus 别名换代也不反映在这一行。属规则设计上的缺口,下次复盘时定要不要再记盲审模型。
- `review-chain.md` 七之一(甲)缩短后,外部 CLI 包装 agent 的两条回报纪律(只返回 `-o` 原文、不可用不许当作无发现)没有去处,而「外部 CLI 包装」这个 low 档 stage 类型还保留着。

结论:U1 通过,U2 通过。链共 2 轮(盲审 1 轮、裁决 1 轮),未到上限。

附带核对(不属于两个单元):本机全局规则相对改前备份只有审计改动块 G24、G25a、G25b 三处不同,逐字与建议替换文本一致;sop-generate 用户级副本的 SKILL.md 与两个脚本和插件版逐字节相同。

用量:实现 1 个 9.1 万、盲审 2 个 18.4 万、修复 1 个 0.9 万、裁决 1 个 13.1 万,合计约 41.6 万 token。实现模型 claude-sonnet-5-5(U2)、claude-opus-5-5(U1,主对话直接改);盲审 claude-opus-5-5;裁决 claude-fable-5-1。
