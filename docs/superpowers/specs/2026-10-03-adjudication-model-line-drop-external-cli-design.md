# 提交里加记裁决模型(小 spec)

日期:2026-10-03。出处:Tony 对上一批遗留项的答复「1. 加上」。同一批里还有几处只涉及内部工具包的改动(文件名里的 drop-external-cli 指的就是那部分),spec 与评审记录在内部仓库,不放在本仓。

## 1. 目标覆盖声明

覆盖目标清单 2026-10-03「1. 加上 2. 去掉 …」一行的 ①。

## 2. Prior art

无外部调研;沿用上一批(`2026-10-03-adjudicator-model-small-spec-workflow-dispatch-design.md`)的镜像面清单。

## 3. 改动

裁决轮省略 `model`、随主对话的模型变,提交正文只记了实现模型,评审模型换代时分不出基线。跑过裁决轮的单元,首个提交正文在「实现模型:」之外再记一行「裁决模型:<裁决轮实际运行的模型 ID>」。

中文(本仓 README.zh-CN.md 第四节规则 4;本机全局规则与内部工具包里的同一句同步改),把

> 核对或补写),统计时按这一行分组,修复轮换过模型的单元单列、不归组

换成

> 核对或补写),跑过裁决轮的单元再记一行「裁决模型:<裁决轮实际运行的模型 ID>」(取法与补写同上;裁决轮随主对话的模型变,不记就分不出评审模型换代),统计时实现模型按「实现模型」行分组,评审基线按「裁决模型」行分段、裁决模型不同的单元不放在一起比,修复轮换过模型的单元单列、不归组

英文 README.md 规则 4,把 `, group by that line, and list a unit` 换成

> ; a unit that ran an adjudication round also gets a line `adjudication model: <the model ID the adjudication round actually ran on>` (taken and filled in the same way — the adjudication round follows the main conversation's model, so without this line a review-model generation change cannot be told apart); group implementations by the `implementation model` line, segment the review baseline by the `adjudication model` line and never compare units with different adjudication models, and list a unit

脚手架模板与 parallel-do 只有压缩句、不带基线条款,不动。

## 4. 验收

- AC1 README 中英规则 4 都有「裁决模型」一行的要求,原「实现模型」要求原样保留;英文与中文含义一致。

## 5. 回滚

`git revert` 对应合并提交;本机全局规则改前有备份。
