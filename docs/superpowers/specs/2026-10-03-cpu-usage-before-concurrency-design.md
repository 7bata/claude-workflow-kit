# 并发前先看 CPU 占用(不再用负载平均值当依据)— 小 spec

日期:2026-10-03。

## 目标

规则「并发前先看负载」原来用 `uptime` 的 1 分钟负载平均值对比核数,判断机器忙不忙。负载平均值数的是排队的任务,不是 CPU 用了多少;进程多的机器上它能比实际占用高出一倍多(实测一台 10 核机器:负载平均值约 10 时,CPU 实际占用 43%~53%),会把半闲的机器判成跑满。改成先看实际 CPU 占用。

## 新规则(README 七之四第 2 条全文)

> 2. **并发前先看 CPU 占用**:并行跑测试、压测、多个浏览器同时截图,以及开跑有多个并行单元的 Workflow 之前,先看机器现在有多忙——CPU 占用取 1 秒采样:macOS `top -l 2 -n 0 -s 1`、Linux `top -bn2 -d1`,取输出里最后一条 CPU 行(macOS 是 `CPU usage` 行,Linux 是 `%Cpu(s)` 行;第一条不准,不用),占用 = 100 − idle(Linux 上写作 `id`);内存看 `memory_pressure`(macOS)或 `free -m`(Linux)。CPU 占用超过 70%,并发数按当前值减半(没设过就按工具默认值算,最少 1);超过 90%,或可用内存低于 20%,改成串行(并发 1)或等占用降下来再跑。`uptime` 的负载平均值不单独作为依据(它数的是排队的任务、不是 CPU 用了多少,进程多的机器上能比实际占用高出一倍多);只有 `top` 取不到读数时才退回按 1 分钟负载对比核数(macOS `sysctl -n hw.ncpu`,Linux `nproc`;超过核数 70% 减半、超过核数串行)。调小的是测试工具自己的并发参数(…原文不变…),派工 prompt 写明本单元测试可用的并发数。报告里写明看到的 CPU 占用、可用内存和实际用的并发数。

其余各处是这条的短写,阈值与命令必须和全文一致:

- 短句(步骤清单、模板里点名规则处):「并发前先看 CPU 占用」。
- 一行写法(模板、parallel-do):先看 CPU 占用(macOS `top -l 2 -n 0 -s 1`、Linux `top -bn2 -d1`,取最后一条 CPU 行——macOS 的 `CPU usage`、Linux 的 `%Cpu(s)`——占用 = 100 − idle;内存 macOS `memory_pressure`、Linux `free -m`):超过 70% 并发按当前值减半(最少 1),超过 90% 或可用内存低于 20% 改串行;`top` 取不到读数时才退回看 `uptime` 的 1 分钟负载对比核数(macOS `sysctl -n hw.ncpu`、Linux `nproc`;超过核数 70% 减半、超过核数串行)。原句后面若跟着别的括注(如「盲审轮同样可以顺序跑」),把它接在「改串行」后面,不要和退回办法的括号挨在一起。
- mechanical 子代理定义里的一句:要并行跑检查时先看 CPU 占用(macOS 用 top -l 2 -n 0 -s 1,Linux 用 top -bn2 -d1,取最后一条 CPU 行,占用 = 100 − idle),超过 90% 就串行跑。

## 改动范围(本仓)

- `README.zh-CN.md` / `README.md`:七之四(7d)第 2 条全文;§四并发上限段末句(「先看一次负载」改成「先看一次 CPU 占用与可用内存」);七.4 步骤「进程约束」里的短句;§四 mechanical 五条通用要求里的那一句。
- 三份脚手架模板(workflow、workflow-en 的 `CLAUDE.md.tmpl`,workflow-codex 的 `AGENTS.md.tmpl`)里对应的各处。
- workflow / workflow-en 的 `agents/mechanical.md` 里那一句。
- workflow-codex 的 `parallel-do` 里两处。
- 三个插件各升一个小版本(workflow / workflow-en 0.17.0,workflow-codex 0.16.0);Progress、DECISIONS 各记一条。
- 镜像:本机全局规则与内部的几处副本同步改,记录在内部仓库。

## 不做

- 章节标题「测试的进程清理与并发负载」不改名(多处按这个名字引用)。
- 减半、串行、分批这些做法不变,只换判断依据与阈值。

## 验收

1. 上述各处不再把「1 分钟负载对比核数」当主判据;负载平均值只出现在「`top` 取不到读数时的退回办法」里。
2. 各处阈值一致:CPU 占用超过 70% 减半,超过 90% 或可用内存低于 20% 串行。
3. 取读数的命令各处一致:macOS `top -l 2 -n 0 -s 1`、Linux `top -bn2 -d1`,取最后一条 CPU 行(不是整份输出的最后一行——实测 macOS 上那是磁盘统计),占用 = 100 − idle。
4. 中英文两份 README 内容对应;各模板保持自己原有的标点风格。
5. 改过的插件 `claude plugin validate` 通过。

## 目标覆盖声明

覆盖目标清单 2026-10-03「改成先看 CPU占用,清了,删」的第①件。第②件见同日的 `2026-10-03-docs-neutral-wording-design.md`。
