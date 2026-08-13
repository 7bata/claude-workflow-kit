# scaffold 新增 BUSINESS.md(业务档案)— Design Spec

> 2026-08-03 ｜ 状态:已获批 ｜ 背景:某批四个内部项目交接暴露的缺口——七件套里 REQUIREMENTS 管"要做什么"、DECISIONS 管"过程中怎么决策",但**"做这个系统之前业务长什么样、为什么值得做"没有家**。这恰是交接时最缺的叙事,也是生成业务 SOP 的原料。

## 决定

七件套 → 八件套:新增 `docs/BUSINESS.md`,scaffold 初始化时落盘。**不改造 REQUIREMENTS 承载业务上下文**(职责分离:BUSINESS 记业务事实,REQUIREMENTS 记产品决定)。

## 改动清单

### 1. 新模板 `templates/docs/BUSINESS.md.tmpl`

结构套用《SOP-系统需求采集手册》7 格模型,**去 Stellark 化的通用措辞**(开源版不引用内部手册名),每节配一行"怎么问/怎么填"的引导注释:

```
# Business — {{PROJECT_NAME}}(业务档案)
> 记录本系统所服务的业务事实:系统出现之前这件事怎么做、业务规则是什么。
> 与 REQUIREMENTS.md 的分工:这里是「业务事实」(相对稳定,采集自业务方),
> REQUIREMENTS 是「产品决定」(我们决定做什么)。业务规则变化先改这里。

## 0. 系统目标与现状手工流程   ← 没系统之前谁、用什么工具、一步步怎么做;痛点在哪
## 1. 触发与频率              ← 什么时候跑、多久一次、谁触发、全量还是增量
## 2. 输入:交易数据           ← 每次都变的数据;★真实样本文件清单(路径登记,文件不入 git)
## 3. 输入:参考/配置数据      ← 对照表、规则表、允许值;★对照表文件登记
## 4. 加工流程                ← 输入怎么变成输出,步骤清单(可从输入列+输出列反推)
## 5. 输出                    ← 产出什么、给谁、什么样;★期望输出样例登记
## 6. 业务铁律与异常          ← 绝不能错的规则;意外情况怎么办
## 7. 人工介入与反馈          ← 谁复核、能改什么、改了要不要被系统记住
## 8. 验收对照                ← 怎么算做对了:对照标准 + 容差
```

### 2. `templates/CLAUDE.md.tmpl`

- 「文档同步规则」表加一行:`业务规则 / 业务流程变化 | docs/BUSINESS.md(业务事实源,先改这里)+ docs/Progress.md`
- 「需求变化」行的说明补一句分工注记:业务事实变化改 BUSINESS,产品范围变化改 REQUIREMENTS

### 3. `SKILL.md`(scaffold 流程)

- 步骤 2 Intake 升级:收集项目意图时**按 7 格模型追问业务上下文**(目标+现状手工流程、输入输出样本、铁律、人工介入);信息不足的格留占位注释,不逼问
- 步骤 4 落盘清单 10 → 11 个文件(加 `docs/BUSINESS.md`),冲突检查循环同步
- 会议纪要归档路径说明补:纪要中的业务事实提炼进 BUSINESS.md(原 REQUIREMENTS 提炼职责拆分)

### 4. 同步范围(四处,措辞各自适配)

| 位置 | 适配 |
|---|---|
| `claude-workflow-kit/plugins/workflow`(开源中文) | 通用措辞 |
| `claude-workflow-kit/plugins/workflow-en`(开源英文) | 英文翻译,结构一致 |
| 内部工具包仓(engineer 版)stellark-scaffold | 可引用内部《SOP-系统需求采集手册》作为 intake 指引 |
| kit 根 README.md / README.zh-CN.md | 提及"七件套"处改"八件套"并列出 BUSINESS |

### 5. 与其他 spec 的衔接(实现时序约束)

- 本 spec 与《branch-push-policy》都改 `CLAUDE.md.tmpl`,与《mirror-and-catalog》都改 scaffold `SKILL.md` → **同仓改动串行执行或合并为一个实现单元**,禁止并行 agent 各改各的
- 交接场景闭环:新项目 day 1 有 BUSINESS.md,未来 HANDOVER 与业务 SOP 从它直接派生

## 验收条款

1. 两个开源版 + 内部版共 3 份 BUSINESS.md.tmpl 落盘,9 节结构齐全;英文版与中文版节节对应
2. 3 份 CLAUDE.md.tmpl 的文档同步表含 BUSINESS 行
3. 3 份 SKILL.md:intake 有 7 格追问指引;落盘清单为 11 文件且冲突检查覆盖
4. README 两个语言版的件套数与文档清单一致
5. `git grep 七件套` 在 kit 内无残留(除历史 spec/research 文档)
