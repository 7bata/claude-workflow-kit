# 评审链:对照 superpowers 6.4.1 的一批规则改动(本仓这一份)

spec:`docs/superpowers/specs/2026-10-05-superpowers-641-approval-gates-and-full-suite-design.md`(单元一:点名新版的批准关口;并行实现时全量测试由主对话按顺序跑)、`docs/superpowers/specs/2026-10-05-review-criterion-and-easy-to-miss-section-design.md`(单元二:评审判据加一句;spec 加一节)。内部的几处副本各自评审,记录在内部仓库。

## 单元一

本仓一个单元(README 中英、两份脚手架模板、两个插件版本号),实现模型 claude-sonnet-5-5(low;按替换清单由脚本套用,套用后核对通过,两个插件 `claude plugin validate` 通过)。

### 第 1 轮 盲审(claude-opus-5-5,medium,2 个,互不可见)

执行:开跑前 CPU 占用 69%、可用内存 39%;与内部单元顺序审,同时只跑 2 个。

没有 P0 / P1,没有结论不一致的条目。评审 A(正确性)逐条核对了验收条款;三句英文原话与 6.4.1 的 brainstorming/SKILL.md 逐字一致;对 HARD-GATE 与 TDD 新增段的转述准确;原来点名的其余各处一字未动;中英文对应。评审 B(边界与异常数据)核对了改动正好是清单的 10 处、公开文本没有内部标识、标点风格、版本号,并照字面推演了只有一个单元、没有 -short、评审者自己跑定向测试等情形。两位都没有跑 `claude plugin validate`(不在给评审的只读命令范围内)。

| # | 严重度 | 位置 | 评审者 | 发现 | 处理 |
|---|---|---|---|---|---|
| K1 | P2 | 两份模板 §7 覆盖那一条 | A、B | 压缩句列两组批准时去掉了路径名,看不出哪组属于哪条路径 | 已改 |
| K2 | P2 | 两份模板 §7 派工那一条 | B | 只写「评审者只读结果」,少了「不再各自跑全量」这个限定,照字面会被读成评审者什么测试都不能跑 | 已改 |
| K3 | P2 | README 七.4(中英)、两份模板 | 内部单元的评审 B 提出,同一句 | 括号里的「这句覆盖 TDD skill……」像是写给主对话的说明,没要求把它写进派工 prompt;6.4.1 的 TDD 原文写着任务里的范围说明不限制验证,实现 agent 可能仍去跑全量 | 已改:写成「并写明这一条优先于……」 |
| K4 | P2 | README 七.4(中英) | A | 「在各单元实现返回后按顺序跑」可以读成要等所有单元都返回,与「每单元完成即派评审链」有点拧 | 遗留 |
| K5 | P2 | README 七.4(中英) | B | 主对话顺序跑全量时出现失败怎么办(归哪个单元、要不要退回)没写 | 遗留 |
| K6 | P2 | README 七.6(中英)、两份模板 | B | 写的是覆盖「HARD-GATE 整段」,这一段里也有 Spike 那一行,句末才说 spike 照原样 | 遗留 |
| K7 | P2 | 两份模板 §7 派工那一条 | B | 漏了 README 里的「(或派一个 agent 串行跑)」 | 遗留 |

### 分流(主对话)

只有 P2 → 判通过,不开裁决轮。K1~K3 压进单元提交(「评审第 1 轮」,清单 `docs/superpowers/specs/2026-10-05-superpowers-641-approval-gates-and-full-suite-round1-fixes.json`);K4~K7 记入 `docs/Progress.md`「待办」表。
