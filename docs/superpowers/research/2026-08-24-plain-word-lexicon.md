# 调研:强制替换用词的词库(2026-08-24)

## 需求

Tony 反馈:AI 汇报里的自造比喻词和行话(「随行注意」「踩在」「未销账目标」)每次都要在脑子里转换成原始含义才能读懂。要一套「行话 → 平实词」的强制映射词库,让 AI 开口就用平实词,一步到位。先查开源有没有现成的,没有就自己建。

## 内部检索

本地 `code-base/components.yaml` 不存在;gitlab.stellark.io 上按 `stellark/code-base` 路径调 API 返回 404。内部组件索引两条路都不可用,如实记录,不阻塞。

## 结论

**没有现成的「中文行话 → 平实词」词库,词库内容必须自己建;但词典文件格式和检查机制都有成熟先例可以照抄。** 调研方式:GitHub API 核实 13 个候选仓库的星数/license/活跃度,再派 6 个并行调研代理逐仓读 README 与词表文件原文(共 67 次工具调用,证据见文末)。

两个关键事实:

1. **机制类工具(prh / Vale / autocorrect)都支持「词A→词B」映射,但没有一个自带中文行话词条**——词典全部要用户自己填。
2. **中文「去AI味」类 skill 管的是另一根轴**:AI 官腔套话(赋能、深入探讨、值得注意的是)和公文腔(进行+动词、予以),不是「自造比喻行话」。唯一精确命中的是 qu-ai-wei 的一条元规则「搭配漂移与心理动作直译」(接住观点、击穿思考这类动作词脱离自然对象 → 换普通动词),但它是一条判断规则,不是可查表的词库。

## 候选对比

### 机制类(词典格式与替换引擎)

| 仓库 | 星/license/活跃 | 映射格式 | 中文可用性 | 判定 |
|---|---|---|---|---|
| [prh/prh](https://github.com/prh/prh) | ★296 / MIT / 2026-08 | YAML:`expected`(目标词)+ `patterns`(多个变体)+ `specs`(自测用例,加载即断言) | 逐字符正则匹配,不依赖分词,中文完全兼容(词条要自己写) | **格式首选** |
| [vale-cli/vale](https://github.com/vale-cli/vale)(原 errata-ai,组织已迁移) | ★5999 / MIT / 2026-08-21 | YAML `swap` map,支持正则、捕获组、一词多个建议 | 默认加 `\b` 词边界,对无空格的中文不可靠,需 `nonword: true` 绕开,官方无 CJK 承诺 | 格式可参考 |
| [huacnlee/autocorrect](https://github.com/huacnlee/autocorrect) | ★1626 / Apache-2.0 / 2026-07 | `词A = 词B` 单行文本(spellcheck.words) | 替换引擎原生处理 CJK 边界(相邻是汉字/中文标点/空白才替换);但 spellcheck 标注 Experimental,默认词典为空 | 文件检查层备选 |

textlint-rule-prh(prh 的 Markdown lint 接入层)只在需要对文档批量 `--fix` 时才有用,不必引入。

### 内容类(现成词条)

| 仓库 | 词条性质 | 与本需求的关系 |
|---|---|---|
| [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh)(★15.9k) | 24 类 AI 腔调词黑名单 + 少量短语级「改写前→改写后」 | 管 AI 官腔,不管自造比喻行话;文件排版结构可抄 |
| [LifelongLazyLearner/qu-ai-wei](https://github.com/LifelongLazyLearner/qu-ai-wei)(★459,2026-08 活跃) | 20+ 条「骨架/触发/保护/动作/复扫」句式规则 | 「搭配漂移与心理动作直译」一条可作词库的元规则(判断哪些词该进词库);无词表 |
| [ren644/de-ai-flavor-skill](https://github.com/ren644/de-ai-flavor-skill) | 中文互联网黑话黑名单(赋能/抓手/闭环/沉淀/链路/复盘…)——只删不换 | 约 10 个词可借入词库,补上平实替换词 |
| [realsigridjin/ai-slop-cleaner](https://github.com/realsigridjin/ai-slop-cleaner) | 英文 banned→replacement JSON(`{"word","replacement","weight"}`)+ 韩语表 | 机器可读词条结构可参考;无中文 |
| [hwajongpark/awesome-slop](https://github.com/hwajongpark/awesome-slop) / [shannhk/avoid-slop](https://github.com/shannhk/avoid-slop) | 工具清单 | 两份清单里都确认**没有**中文受控词表项目 |

([jalaalrd/anti-ai-slop-writing](https://github.com/jalaalrd/anti-ai-slop-writing) ★405 为纯英文黑名单,无映射、无中文,仅参考。)

## 采用方案(建议)

自研词库内容,格式与机制照抄现成:

1. **词库文件**:借 prh 的结构(一个平实词 ← 多个行话变体,每条可带自测用例),对人展示用 markdown 表格。
2. **生效位置**:对话输出没有「生成后改写」的钩子可用,唯一能强制的位置是**生成前注入**——复用 speak-human 已有的开局注入通道,词库作为新纪律(暂名 S5)常驻。
3. **可选检查层**(后做):对文档/文案文件,可用 autocorrect 的 `词A = 词B` 配置或几十行脚本做机器检查,防止词库只靠自觉。

词库内容三个来源:Tony 点名的词、AI 汇报里的高频同类词(待 Tony 圈选)、de-ai-flavor-skill 黑名单中同类词补上替换词。

## 词库草案 v0(待 Tony 圈选)

见对话中呈现的草案表;定稿后按 speak-human 分发流程进权威源与四个分发处。

## 证据

- 星数/license/活跃度:GitHub API `/repos/<owner>/<repo>` 逐一核实(2026-08-24)。
- prh:读了 README.md、misc/prh.yml(词典范例)、lib/rule.ts(匹配引擎)、lib/raw.ts(格式定义)。
- autocorrect:读了 README、.autocorrectrc.default(默认词典为空)、src/rule/spellcheck.rs、src/config/spellcheck.rs、src/keyword.rs(Aho-Corasick 引擎与 CJK 边界判断)。
- Vale:curl -sI 确认 errata-ai/vale 301 → vale-cli/vale;读了 docs.vale.sh/checks/substitution 全文、issue #356(多语言 NLP 方向已 Closed as not planned)、LICENSE。
- Humanizer-zh:SKILL.md 全文(18898 字节,仓库仅 4 个文件);qu-ai-wei:SKILL.md + references/pattern-catalog.md 等 6 个规则文件 + tests 脚本(CI 只做静态格式校验)。
- de-ai-flavor-skill / anti-ai-slop-writing / ai-slop-cleaner:各自词表文件原文。
- awesome-slop:README + 其配套 slop-gate/rules/chinese.json 全文(7 条公文腔正则);avoid-slop:README 全文。
