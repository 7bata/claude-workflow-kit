# 提交里加记裁决模型 + 内部工作流 skill 的盲审去掉外部 CLI(小 spec)

日期:2026-10-03。出处:Tony 对上一批遗留项的答复「1. 加上 2. 去掉」。

## 1. 目标覆盖声明

覆盖目标清单 2026-10-03 一行的 ① 与 ②。不覆盖:③(huake 插件名,Tony 说先不管)、prompt 审计的建议改动块(Tony 还在看)、内部工具包核心 skill 的 6500 token 目标(另有待办)。

## 2. Prior art

无外部调研;沿用上一批(`2026-10-03-adjudicator-model-small-spec-workflow-dispatch-design.md`)的镜像面清单。

## 3. 改动

### 3.1 加记裁决模型(通用规则,四个完整句的面 + 内部核心压缩句)

裁决轮省略 `model`、随主对话的模型变,提交正文只记了实现模型,评审模型换代时分不出基线。跑过裁决轮的单元,首个提交正文在「实现模型:」之外再记一行「裁决模型:<裁决轮实际运行的模型 ID>」。

中文三处(本机全局规则、本仓 README.zh-CN.md 第四节规则 4、内部工具包 WORKFLOW.md 规则 4),把

> 核对或补写),统计时按这一行分组,修复轮换过模型的单元单列、不归组

换成

> 核对或补写),跑过裁决轮的单元再记一行「裁决模型:<裁决轮实际运行的模型 ID>」(取法与补写同上;裁决轮随主对话的模型变,不记就分不出评审模型换代),统计时实现模型按「实现模型」行分组,评审基线按「裁决模型」行分段、裁决模型不同的单元不放在一起比,修复轮换过模型的单元单列、不归组

英文 README.md 规则 4,把 `, group by that line, and list a unit` 换成

> ; a unit that ran an adjudication round also gets a line `adjudication model: <the model ID the adjudication round actually ran on>` (taken and filled in the same way — the adjudication round follows the main conversation's model, so without this line a review-model generation change cannot be told apart); group implementations by the `implementation model` line, segment the review baseline by the `adjudication model` line and never compare units with different adjudication models, and list a unit

内部工具包核心 skill 规则 4 末句「实现模型换代按提交正文「实现模型:」行分段。」后半改为「实现模型换代按提交正文「实现模型:」行分段,评审基线按「裁决模型:」行分段(跑过裁决轮的单元记)。」

脚手架模板、parallel-do、huake 两个工具包只有压缩句、不带基线条款,不动。

### 3.2 内部工作流 skill 的盲审去掉外部 CLI(只动内部工具包)

评审链回到与上游相同的形态:盲审 2 个互不可见的 `opus` + `medium`(规则 3 单元 3 个、每轮 `high`、第三个加安全镜头),续挖 `opus` + `medium`,裁决轮用主对话当前的模型 + `high`;上限回到默认 4 轮(盲审算一轮),不再按链数计。「重要评审不许只用 opus 单一模型」一句删除。外部 CLI 的两个驱动 skill 保留,只在用户点名时用,不属于评审链。

要改的地方:
- 核心 skill:开头说明句(本仓 delta 不再含异构评审链)、分工表评审行、档位表盲审行、规则 2 入口句(「派任何评审子代理前,读 references/review-chain.md」)、规则 3(盲审 3 个 opus)。入口句与「不许 / 禁止 / 必须 / 一律」的出现次数只许因删掉的那一句减少,其余不变;token 只许不增加(基线 6532.0,公式见该仓 `docs/reviews/2026-09-23-slim-c/c1-map.md`)。
- `references/review-chain.md`:三.2 改成上游的写法(盲审两个 opus、合并规则、续挖、裁决、分流、修复与接续、4 轮上限、Workflow 里的写法),保留本仓独有的 spec/plan 评审 (a)(b)(c) 与收敛判定(「连续 2 条链」改成「连续 2 轮裁决」的等价说法)、测试资源卫生三条;「七之一(甲)」整节换成两三句:外部 CLI 只在用户点名时按两个驱动 skill 用,产出由主对话裁决,不占评审链的位置。
- `references/upstream-map.md`:delta 清单去掉异构评审链与七之一(甲),补一条本批记录。
- 两个驱动 skill 的 description 与正文里「评审链需要外部 CLI 一方」「异构评审轮 / 票」的说法改成「用户点名时」;README 的 skill 表与 stellark-workflow 一行同改;parallel-do 里把外部 CLI 当评审链一方的句子同改(「外部 CLI 包装」这个 low 档 stage 类型保留)。
- 行为有变:插件版本升到 1.8.0,README 版本说明加一行。

## 4. 验收

- AC1 四个完整句的面都有「裁决模型」一行的要求,原「实现模型」要求原样保留;英文面对应。
- AC2 内部核心 skill、review-chain.md、WORKFLOW.md、README、parallel-do、两个驱动 skill 里搜不到把外部 CLI 写成评审链固定一方的句子;两个驱动 skill 仍在、可点名使用。
- AC3 核心 skill token ≤ 6532.0;「不许」「禁止」「必须」「一律」与 `references/` 入口的次数变化都能对应到 3.2 删掉的句子。
- AC4 review-chain.md 保留 spec/plan 评审 (a)(b)(c)、测试资源卫生三条、分流规则、修复不在评审 stage 里做。
- AC5 `claude plugin validate` 对内部工具包的结果不比改前差。

## 5. 回滚

全局规则:`cp ~/.claude/CLAUDE.md.bak-20261003-adjudicator-model-line ~/.claude/CLAUDE.md`。两个仓:`git revert` 对应合并提交。

## 6. 追加:Stella 记录子代理的语言(同一分支合并,单独一个单元 U3)

出处:Tony 2026-10-03 在 hapi 窗口说「更新stella的为啥是英文,调成中文的」,由该窗口转来。现象:批次收尾时子代理的回执整段是英文,待办标题也被译成英文;子代理定义与 stella3 skill 都没有规定语言。

改动(评审第 1 轮后的定稿):内部工具包 `agents/stella-recorder.md`「给用户的话」一节加一条——标记之间给用户的话,以及子代理自己组织后写进 Stella 的文字(标题、描述、原因、工时备注、更新日志正文),一律用中文;别人给的原文照原样、不翻译不改写:用户原话或批次清单里明确给出的标题、名称、原因、标签名(各节「原话直接用」的规定照旧),已有待办标题,工具返回的原文,编号、链接、代码标识符、人名、项目名与专有名词。stella3 skill 只转发子代理原文,不用改。写回 stella 仓原稿时以内部工具包里的那一条原文为准。

验收:AC6 子代理定义里有这条语言规定,位置在每次返回都会读到的「给用户的话」一节;其余内容不变。合并并更新本机插件后,这一批自己的 Stella 收尾回执是中文。

遗留:这两个文件的原稿在 stella 仓,那边要写回同样的改动,否则下次同步会覆盖。
