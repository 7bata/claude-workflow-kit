# REQUIREMENTS

## 目标台账(收件箱)

| 日期 | 原话 | 出处 | 状态 |
|---|---|---|---|
| 2026-08-14 | "一会stella窗口会给你发一个任务,你记得改的时候把huake/stellark/github/本机四个版本全部更新一下" | Tony 对话(claude-workflow-kit 会话) | done — 四面已并 main(2026-08-14 Tony「合并」门禁):kit 7f6c23d、dev-toolkit 1.3.0(9306293)、claude-toolkit-engineer 0.15.0(66d65d9),wip 分支已删;本机 settings.json 已生效 |
| 2026-08-14 | "(DECISIONS 自动采集)我觉得得做,而且你把这个交给 claude-workflow-kit 这个窗口的 session 吧" | Tony 原话,经 stella 主会话转达 | done — `docs-capture-hooks-design.md` §3 三层全部实现并落四面(层 2 经五轮定案为高召回软提醒) |
| 2026-08-14 | "另外也让它检查一下其他的几个 docs 到底有没有自动更新的功能"(审计 Progress/PLAN/REQUIREMENTS/ARCHITECTURE 等自动更新现状,给清单式结论再补齐) | Tony 原话,经 stella 主会话转达 | done — `docs/superpowers/research/2026-08-14-docs-auto-update-audit.md` |
| 2026-08-14 | 审计发现 kit 八件套与 stellark starter 六件套两套文档契约分叉,生产侧 /stellark-setup-prod 仍在用 starter;Tony 问"starter不是早就弃用了吗"——需拍板:生产 setup 去 starter 化,或 starter 模板与 kit 契约对齐(涉及龙哥共同维护面,单独开批次) | 本会话审计 + Tony 追问 | open — 拍板已定「本批不做只登账」(见下条),单独批次未开 |
| 2026-08-14 | 本批范围拍板:DECISIONS 自动采集 + 漏更提醒门禁 + REQUIREMENTS 台账捕获三件一起做;两套契约收敛不做只登账 | Tony 选项作答 | done — 三件均见 `docs-capture-hooks-design.md`,四面交付完毕 |
| 2026-08-14 | 层 2 收尾拍板:高召回软提醒定案(提示语自免疫,验收标准改"领域内误报可忽略") | Tony 选项作答 | done — spec §3 层 2 定案条款 + 两语言实现 |
