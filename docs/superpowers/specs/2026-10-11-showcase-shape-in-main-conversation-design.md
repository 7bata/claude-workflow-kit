# 展示型前端:方向在主对话定、子代理只做建造 —— 设计

日期:2026-10-11。依据:目标清单 2026-10-11「核对 impeccable 自带流程……子代理问不了人」一行,用户答「可以」(照建议改规则)。

## 目标覆盖声明

- 覆盖:目标清单 2026-10-11「核对 impeccable 自带流程(shape.md、new-work.md)……」一行(open);顺带关掉同日评审链遗留的 P2「本机规则缺 hallmark 保留句」。
- 不覆盖:同日遗留 P2 里内部工具包核心第 50、52 行的括注与空格(另一批字数问题);text-overflow 等四条硬闸门规则的补测(要等真阳性样本);国内平台抓取调研(用户未定)。

## Prior art

impeccable 4.5.2 自己的流程已经分段:`reference/shape.md`(发现式访谈,「用提问工具问两三轮,然后等」)、`reference/new-work.md` 第 2 节「问什么会改变结果」、第 3~4 节(方向卡由使用者选定一张,`concept-seed` / `serve-question`)、第 5 节「记录决定」(direction contract 写进 surface brief,批准的样稿在 `.impeccable/mocks/decision/`)、第 6 节「建造」、第 7 节「检查与收尾」(finish reviewer)。要问人的全在第 5 节之前,建造从第 6 节起。本批只按这条分界切开主对话与子代理的分工,不引入新工具。

## 一、规则改动(三条)

下面是本机全局规则(中文)的目标措辞;公开仓 README 中文面同义改写(不写本机路径),英文面按中文面翻译;脚手架模板与内部工具包按各自现有的压缩程度改写,要素不丢。

### A. brainstorming 阶段:展示型前端的方向由主对话定

直通流程第 0 步(README 七.1、WORKFLOW.md 七.1)末尾加一段:

展示型前端(分类按角色表「前端美术」行)的**新页面或换视觉风格**,brainstorming 里由主对话(不是子代理)先用 Skill 工具调用 `impeccable`:该项目还没有 PRODUCT.md 时先 `/impeccable init`,再 `/impeccable shape`,接着走它 new-work 流程到第 5 节「记录决定」为止——第 2 节的提问与第 3~4 节的方向卡选定,用提问工具转给使用者答、由使用者选定;direction contract 写进 surface brief、批准的样稿落在 `.impeccable/mocks/decision/`。spec 里写明 surface brief 路径、direction contract 所在位置与批准样稿的路径,子代理不再问人。局部扩展(既有页面加一个区块或组件)与既有页面的打磨不走这段,直接派子代理。

### B. 派工句:子代理只做建造或打磨

直通流程第 2 步(README 七.4、WORKFLOW.md 七.4、内部 `references/frontend.md` 派工节)的展示型句改写:

展示型前端的 stage prompt 第一步写明先用 Skill 工具调用 `impeccable` **做建造**:新页面或换视觉风格按 spec 里已定的方向、direction contract 与批准的样稿,从 new-work 第 6 节「建造」起做到第 7 节收尾;局部扩展走 new-work 的「扩展既有页面」路径;既有页面的打磨走 `/impeccable polish`;审查走 `/impeccable critique`(手动入口,不进评审链;不变)。init、shape 与方向选定不派给子代理——它们要用提问工具问人、让人从方向卡里选一张,子代理问不了,已在 brainstorming 由主对话做完。建造或 polish 过程中 impeccable 要问人的地方,子代理按 spec、PRODUCT.md、DESIGN.md 自行判断并把判断写进返回,不编造使用者偏好。其余要素原样保留:本机已装为用户级 skill、它第一步跑 `impeccable context`、没装的机器用 hallmark / frontend-design、hallmark 保留不删且双触发再去掉(本机全局规则此前缺这一句,本批补上)、避开清单以 detect 套路类规则为基线逐轮补、管理后台与内部工具界面不调用设计 skill、不装 hook / 不开 live / critique 不进评审链。

### C. 角色表「前端美术」行

各面(全局、README 中英、WORKFLOW.md、内部核心 SKILL.md 第 18 行、内部 parallel-do 第 11 行、三份脚手架模板的派工句)里「展示型前端先调设计 skill」这类说法,改成「展示型前端:方向由主对话用设计 skill 定(init / shape / 选方向卡),子代理只做建造或打磨」,按各面现有压缩程度改写。

## 二、同步面与单元划分

| 单元 | 面 | 档位 |
|---|---|---|
| U1 本机全局 | `~/.claude/CLAUDE.md`:直通流程第 0 步(A)、第 2 步展示型句(B,含补 hallmark 保留句)、角色表前端美术行(C);改前备份 `~/.claude/CLAUDE.md.bak-20261011-shape-main` | sonnet + medium |
| U2 公开仓 | `README.zh-CN.md` 七.1(A)、七.4 展示型句(B)、角色表前端美术行(C);`README.md` 对应英文面;`plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl` 与 `plugins/workflow-en/...` 第 124 行派工句(B+C 压缩句)与 §7 第 96 行 brainstorming 条(A 压缩半句);两个 `plugin.json` 0.19.0 → 0.19.1;`claude plugin validate --strict` 两个插件 | sonnet + medium |
| U3 内部工具包(`~/Tony/Proj/Stellark/Platform/dev-toolkit`,建 wip 分支 `wip/showcase-shape-main-2026-10-11` 提交并推送) | `WORKFLOW.md` 七.1(A)、七.4 展示型句(B)、角色表前端美术行(C);`plugins/dev-toolkit/skills/stellark-workflow/references/frontend.md`(派工节按 B 改写,新增「brainstorming 里主对话先做的」一节按 A,分类节不动);核心 `stellark-workflow/SKILL.md` 第 18 行角色表句(C 压缩句;改后核心字数 ≤ 6500,前后数字记进返回);`stellark-parallel-do/SKILL.md` 第 11 行(C 压缩句);`stellark-scaffold/templates/CLAUDE.md.tmpl` 第 128 行派工句(B+C)与第 100 行 brainstorming 条(A 压缩半句);`references/upstream-map.md` 记本批;该仓 `docs/Progress.md` 加条目 | sonnet + medium |

每个单元的 FORBIDDEN FILES:不属于本单元那一列的任何文件;U2 不得改 `docs/` 下除本 spec 以外的文件(Progress 与评审链由主对话写);U3 不得改公开仓与本机文件;U1 只改那一个文件。所有单元:绝不重启共享服务、绝不读写生产数据、禁止 force push 与丢弃改动的历史改写;本批不需要启动任何进程。

## 三、验收条款

1. 全局 CLAUDE.md、README 中英、WORKFLOW.md:第 0 / 七.1 步含「主对话」「`/impeccable shape`」「第 5 节」「方向卡」「spec」;派工句含「做建造」「第 6 节」「不派给子代理」「polish」「不编造」;角色表前端美术行含「主对话」「建造」;hallmark 保留句三面都有(本机全局规则此前缺)。关键词 `grep -c` 每面 ≥ 1,且评审人工核对要素齐、前后不矛盾。
2. 三份脚手架模板:派工句含「方向由主对话用 impeccable 定(init / shape / 选方向卡)」「子代理只做建造或 polish」;§7 brainstorming 条含「展示型前端新页面或换风格,主对话先跑 `/impeccable shape`、方向写进 spec」半句;kit 两个插件版本 0.19.1,`claude plugin validate --strict` 通过。
3. 内部工具包:`references/frontend.md` 新节与派工节到位;核心 SKILL.md 字数 ≤ 6500 并记前后数字;parallel-do 第 11 行已改;upstream-map 记本批;wip 分支已推送。
4. 备份文件 `~/.claude/CLAUDE.md.bak-20261011-shape-main` 存在且与改前一致。
5. 公开面(README 中英、两份模板)不含本机路径与内部名。

## 四、容易漏的输入与失败情形

1. **项目已有 DESIGN.md、只是加一个新页面**(new-work「在既定世界里建整页」):仍要 shape 和方向卡选定(`concept-seed` 让使用者选一张),所以也归主对话——措辞用「新页面或换视觉风格」,不只写「换风格」。U1 / U2 / U3 措辞核对。
2. **局部扩展**(既有页面加一个区块或组件,new-work「扩展既有页面」路径):impeccable 自己说不跑 concept-seed、直接 shape,不问人就能做——归子代理,规则写明「局部扩展与既有页面打磨直接派子代理」。措辞核对。
3. **子代理在建造 / polish 里仍碰到要问人的地方**(polish:「推不出约束性的系统原则时问人」):合理预期是不卡住、不编造——规则写明按 spec / PRODUCT.md / DESIGN.md 判断并写进返回。措辞核对。
4. **主对话跑 shape 时 impeccable 用 `serve-question` 起本地决策页让人选卡**:用户在 HAPI 手机端看不到本机页面;impeccable 自己写「有结构化提问工具就用它,否则问完停下」,规则不另写;记进评审链,等第一次实跑核对。
5. 已检查,其余没有。

## 五、评审

每单元盲审 2 个(opus + medium;镜头 A 正确性:要素齐、各面前后不矛盾、该改的锚点全改到;镜头 B 边界:第四节四条情形覆盖、三面说法一致、公开面不含内部名与本机路径),脚本按 file + line 归并并标 conflict;有 P1 修复后裁决(opus + high);有 P0 修复后续挖再裁决。本批不触及规则 3 的不可逆操作。评审链记录:`docs/reviews/2026-10-11-showcase-shape-main-chain.md`(内部工具包单元的细节记在该仓)。
