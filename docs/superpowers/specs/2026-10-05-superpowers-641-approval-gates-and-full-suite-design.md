# 对照 superpowers 6.4.1:点名新版的批准关口;并行实现时全量测试由主对话按顺序跑 — 小 spec

日期:2026-10-05。

## 目标

superpowers 从 6.3.0 升到 6.4.1。2026-10-04 做了一次只读对照(5 个 agent 对照、2 个逐条核对),查出两处会把按本规则干活的 agent 往相反方向带。Tony:「那就把1和2改一下,按照我们自己workflow的规则,目前我们已有的这个规则挺好的」。两处都以本规则为准,不吸收新版的其他做法。

## 两处改动

### 1. 七.6 改写 brainstorming 批准关口的那一条,点名 6.4.1 的写法

6.4.1 把 brainstorming 的 HARD-GATE 整段重写:按路径列出实现前要过的批准(spike 批准问题与探测;bounded 批准对话里的短设计;架构路径先批准书面 spec、再审阅书面实现计划并选定执行方式),并新增三句——"written-spec approval only permits invoking writing-plans"、"A reply approves the stage actually presented"、"do not turn one approval into permission to skip the rest of the selected path"。这三句与「spec 写入即授权、直接实现」正面相反。原来点名的各处(架构路径清单第 8、9 项、User Review Gate、"the ONLY skill you invoke after brainstorming is writing-plans"、bounded 停下等批准、"Too Simple To Need Approval" 一节)在 6.4.1 里都还在,照留。

新写法:七.6 里原来的「HARD-GATE 里『每条路径都要先获批准才能实现』」换成「HARD-GATE 整段」,写出 6.4.1 按路径列的批准,点名上面三句,并补一句:spec 写入就是对其后全部阶段的授权,不按阶段逐次请示,执行方式就是 Workflow 编排、不另选(用户点名别的方式时除外)。spike 路径照 brainstorming 原样,它那一条前置条件不覆盖。

脚手架模板 §7 原来只写了「覆盖『不写 spec、停下等批准』」,补上 HARD-GATE 整段与 "A reply approves the stage actually presented" 一句(压缩版)。

### 2. 七.4 派工要求:多个单元并行实现时,全量测试由主对话按顺序跑

6.4.1 的 test-driven-development 新增一段:收尾前要跑项目的全量测试,即使任务只点名一个测试文件;跑出来的每个失败(含不是自己造成的)按名字写进报告。多个单元并行实现时,每个实现 agent 照做就会同时各跑一遍全量。

新写法(加在七.4「进程约束」里、「并发前先看 CPU 占用」之后):多个单元并行实现时,同一时间只允许一个单元跑全量或重型测试;派工 prompt 写明实现 agent 收尾只跑本单元的定向用例或 -short、不跑项目全量——这句覆盖 TDD skill 里收尾前跑项目全量测试的要求;「跑到的失败按名字写进报告」不覆盖,照做;全量由主对话在各单元实现返回后按顺序逐单元跑(或派一个 agent 串行跑),结果交给评审,评审者只读结果、不再各自跑全量。脚手架模板 §7 派工那一条加一句压缩版。

只有一个单元、没有并行时不受这句限制,照 TDD 与「并发前先看 CPU 占用」办。

## 不动

- 对照时列出的其余几条(评审结果加「搁置不判的事项」、spec 没写到的行为按使用者的合理预期判、spec 加一节容易漏的输入与失败情形、评审前先确认有改动可审、脚本调用带解释器、inline 与 Native 两个叫法、写回理解与「先复述再动手」的衔接、记下核对过的版本)——Tony 定:现有规则不变。
- Codex 版(模板与 parallel-do):那一侧没有 superpowers,两处冲突都不存在。
- whats-next:只是指路表,覆盖说明放在模板里。
- 七.2、七.7 与评审链协议。

## 改动范围(本仓)

逐条的改前改后文字在同目录 `2026-10-05-superpowers-641-approval-gates-and-full-suite-replacements.json`(10 条;每条的 old 在目标文件里恰好出现一次):`README.zh-CN.md` 与 `README.md` 各 2 处(七.6、七.4);workflow 与 workflow-en 的 `CLAUDE.md.tmpl` 各 2 处(§7 两条);两个插件版本号 0.17.0 → 0.18.0。Progress、DECISIONS 各记一条。镜像:本机全局规则与内部的几处副本同步改,记录在内部仓库。

## 验收

1. 七.6(中英)点名 HARD-GATE 整段、6.4.1 按路径列的批准与上述三句英文原话;三句原话与 6.4.1 的 brainstorming/SKILL.md 逐字一致;原来点名的其余各处一字不动。
2. 七.4(中英)写明:并行时同一时间只允许一个单元跑全量、实现 agent 收尾只跑定向用例、这句覆盖 TDD 的收尾全量要求、失败照样按名字报、全量由主对话按顺序跑并把结果交给评审。
3. 两份模板各有对应的压缩句,保持原有的标点风格(中文模板用全角标点);中英文内容对应。
4. 除替换清单列出的 10 处外,本仓的 README 与插件没有别的改动;公开文本里没有内部标识。
5. 改过的两个插件 `claude plugin validate` 通过。

## Prior art

不涉及新子系统,没有做外部调研。依据是 superpowers 6.3.0 与 6.4.1 的原文对照:brainstorming/SKILL.md 的 HARD-GATE 一段、test-driven-development/SKILL.md 新增的一段。

## 目标覆盖声明

覆盖目标清单 2026-10-05「那就把1和2改一下,按照我们自己workflow的规则,目前我们已有的这个规则挺好的」;2026-10-04「superpowers插件更新了……看看……有没有什么需要更新改进的地方」随之标记完成。不覆盖对照时列出的其余几条(Tony 定现有规则不变)。
