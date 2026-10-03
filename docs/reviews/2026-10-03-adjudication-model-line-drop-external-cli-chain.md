# 评审链:提交里加记裁决模型

spec:`docs/superpowers/specs/2026-10-03-adjudication-model-line-drop-external-cli-design.md`。本仓单元 U1(README 中英规则 4 各一句,提交 6fba19e,主对话直接改,实现模型 claude-opus-5-5);本机全局规则同一句同步改。同一批里只涉及内部工具包的单元,评审记录在内部仓库。规则文字单元,没有测试,对照实验不计入。

## 第 1 轮:盲审(2 个 opus + medium,互不可见,顺序跑)

U1 无发现。两位都核对过:README.zh-CN.md 与 README.md 只有规则 4 各一处改动,中文与 spec 的替换文本逐字一致,英文与中文含义一致、语法通顺,原「实现模型 / implementation model」要求原样保留。

## 第 2 轮:裁决(省略 model,实际运行在 claude-fable-5-1,high)

U1 通过。与本仓有关的新发现(P2,记遗留):
- 英文 `README.md:222` 新句用 adjudication round,同文件其余处都叫 verdict round(用词出自 spec 原文)。
- 「裁决模型」行只记裁决轮:盲审直接判通过的单元没有这一行,盲审与续挖的 opus 别名换代也不反映在这一行。下次复盘时定要不要再记盲审模型。

新规则当批就用上:U1 的提交正文记了「裁决模型:claude-fable-5-1」。
