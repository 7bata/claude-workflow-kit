# 评审链:本机 mod workflow-guard(U1)

spec:`docs/superpowers/specs/2026-10-03-workflow-guard-local-mod-design.md`。代码仓:本机 `~/Tony/Proj/Stellark/Projects/claude-local-mods`(暂无远端),分支 `wip/workflow-guard-v1`,首个提交 aa022a2。

实现:claude-sonnet-5-5 + medium(对照实验 S 组),TDD;`claude plugin validate` 通过,`claude plugin test` 123 过 0 败;用 npx 临时装的 tsc 类型检查 0 错误。约 17.8 万 token。

## 第 1 轮:盲审(2 个 opus + medium,顺序跑;各自重跑了 validate 与 test)

两位都把所有发现标为 P2。主对话合并后的清单(R = 正确性镜头,E = 边界镜头):

| # | 位置 | 发现 | 谁报的 | 主对话定级 |
|---|---|---|---|---|
| W1 | `host.ts` 无会话名记为 default | 默认会话全机共用,本会话结束时会关掉别的会话正在用的浏览器 | R、E | P1(违反「只关自己启动的」,属 spec 4.2 的缺口) |
| W2 | `host.ts` 切段 | heredoc 正文里以 agent-browser 开头的行被当成真调用,可能记下并关掉别的会话的浏览器 | E | P1(同上) |
| W3 | `register.tsx:300` | 只看 `deny` 不看 `isError`:失败的 close 也把名字从清单与 store 删掉,浏览器无声泄漏;失败或被下层拒绝的打开照样记账 | R、E(测试缺口) | P1(漏关且不报残留,与 4.3 / 4.4 的目的相反) |
| W4 | `host.ts:147` | 带值选项的值被当成子命令(`--profile /p close` 记成打开) | R、E | P2 |
| W5 | `host.ts:151` | `--session "$NAME"` 记下字面量,关不掉也不报残留 | R、E | P2 |
| W6 | `host.ts:115` | `timeout 30 agent-browser`、`npx agent-browser@x`、`$(...)`、子 shell、`bash -c` 不认 | E | P2 |
| W7 | `register.tsx:220` | `session.start` 串行等多条命令,卡住时首个提示被拖 25 秒以上 | R | P2 |
| W8 | `register.tsx:163` | 结束时逐个 close 没有总时长上限 | E | P2 |
| W9 | `register.tsx:229` | 定时器只在 `session.start` 起,模块重载后状态栏一直显示旧负载 | E | P2 |
| W10 | `register.tsx:149` | `close --all` 漏删同一条命令里刚写入的 store 记录 | E | P2 |
| W11 | `scan.ts:238` | 名叫 agent 的对象 / 类方法定义被当成调用,合规脚本被拦;`foo . agent(` 也算 | E | P2 |
| W12 | `scan.ts:82` | 关键字后的正则字面量被读成除号,扫描器抛错后整次检查放行 | E | P2 |
| W13 | `host.ts:4` | 负载解析不认逗号小数 | E | P2 |
| W14 | 测试 | 缺:被拒 / 出错的 Bash 不记账;关键字后的正则;名叫 agent 的方法;很窄的状态栏;「不是文本」用例没走到出错路径 | R、E | P2(随修复补齐) |
| W15 | `register.tsx:108` | 第 2 项检查假设不带前缀的 `mechanical` 解析不到,但本批没有重新验证 | E | P2(放进 AC8) |

两位都核对通过的点:4.1 判定表逐行;出错放行的每条路径;多项违规合并成一条;结束时只遍历本会话的清单;残留只提示不关;每条外部命令都带超时;非交互会话不起定时器;没有常驻进程;状态栏两个界面;断言检验的是行为。

分流:主对话把 W1、W2、W3 定为 P1(盲审标 P2,定级理由见表)→ 修复后裁决。spec 加 4.7 修订 (a)~(m),AC8 加一步。修复按打回流程:测试与实现分开两个 agent(sonnet + high),先补测试再改实现。
