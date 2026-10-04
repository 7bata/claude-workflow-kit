# 评审链:并发前先看 CPU 占用 + 裁决轮改回固定用 opus(本仓这一份)

spec:`docs/superpowers/specs/2026-10-03-cpu-usage-before-concurrency-design.md`、`docs/superpowers/specs/2026-10-03-adjudication-round-back-to-opus-design.md`。本仓一个单元(README 中英、三份脚手架模板、两份 mechanical 定义、codex 的 parallel-do、三个插件版本号),实现模型 claude-sonnet-5-5(medium)。内部的几处副本各自评审,记录在内部仓库。

## 实现之前:spec 的一处错

CPU 占用 spec 第一版的一行写法与 mechanical 那句写的是「取最后一行」。先在内部副本上实现并盲审时被查出:照字面取到的不是 CPU 行(实测 macOS 上 `top -l 2 -n 0 -s 1` 整份输出的最后一行是磁盘统计,Linux 上是一条进程记录)。spec 改成「取最后一条 CPU 行(macOS 的 `CPU usage`、Linux 的 `%Cpu(s)`)」,一行写法补回取核数的命令,并写明别的括注要接在「改串行」后面。本仓的单元是按改过的 spec 实现的。

## 第 1 轮 盲审(claude-opus-5-5,medium,2 个,互不可见)

执行:开跑前 CPU 占用 64%、可用内存 42%(没到 70%,不减并发)。

没有 P0 / P1,没有 conflict。评审 A(正确性)核对了两份 spec 的验收条款、越界、中英文对应、版本号,三个插件 `claude plugin validate` 通过;评审 B(边界)在本机实跑了取读数的命令,照字面能得到 0~100 的占用。

| # | 严重度 | 发现 | 处理 |
|---|---|---|---|
| K1 | P2 | 英文 mechanical 定义里的减号用了 ASCII 连字符,与其余各处不统一 | 已改 |
| K2 | P2 | mechanical 那一句没写 `top` 取不到读数时怎么办 | 遗留 |
| K3 | P2 | 模板与 parallel-do 的一行写法没带「没设过就按工具默认值算」这半句 | 遗留 |
| K4 | P2 | Linux 上打开逐核显示、busybox 的 top、逗号小数点的语言环境下,照字面取不到 `%Cpu(s)` 行或读不出 id(各处都有退回办法,影响有限;Linux 没有实测) | 遗留 |

## 分流(主对话)

只有 P2 → 判通过,不开裁决轮。K1 压进单元提交;K2~K4 记入 `docs/Progress.md`「待办」表。
