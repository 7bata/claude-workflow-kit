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
| 2026-08-24 | "把这种设计上需要简洁的这个原则,告诉 claude-workflow-kit 那个会话,让他把我电脑上的、stellark、huake、github 开源这四个地方的 /speak-human skill 重新写一下。"(原则:简洁,不过度解释——一个区块一句话;写结果不写机制;一个事实只说一次;不堆术语;不给图配注释;不要"其实/本质上/换句话说"这类解释性连接词;能删的先删再交付) | Tony 原话,经 askthestalks-48 会话转达 | done — S4 已并权威源 main(5ee48cd,RED 0/3→GREEN 强制项 3/3,三轮链式评审收敛);四面同步:本仓已并 main(871e50d)、dev-toolkit 已并 main(b0dc426,CI auto-bump)、本机 symlink 重建;claude/codex-toolkit-engineer 已本地并 main、待推(huake GitLab 的 80/2222 从 LAN 进 WSL 被拦,portproxy 表正确、WSL 内部健康,需上机排查) |
| 2026-08-24 | "现在的问题在于,虽然很简洁了,但是依旧不够清晰。比如"把流年起伏画成一条线。"这句话是什么意思?你要做的是,又简洁,又明了,让人一下就能看懂你想表达什么。"(S4 定名「简洁且明了」:删完剩下的那句必须是读者视角的结果,不是系统视角的机制;可检查写法是「明了测试」) | Tony 原话,经 askthestalks-48 会话转达 | done — 已并入 S4 定稿(「明了测试」为交付前第二道自检),见上 |
| 2026-08-24 | "最大的问题是你的用词(名词/谓语选用):随行注意、踩在、未销账目标这类。正常说需注意、待做目标就行。你先去 github 看看有没有强制让你转化表达的词库,没有的话我们自己搭一套——看你说话太费劲,总要转化你用词的原始含义,直接一步到位最好。" | Tony 原话(本会话) | open — 调研完成(无现成中文词库,报告见 research/2026-08-24-plain-word-lexicon.md);Tony 认可词库草案并追加"prompt 里加通用原则"要求;已实现为 speak-human S5(20 条词库+通用原则+四条豁免),评测改前 1/3→改后 3/3 达线,三票评审意见修完,四个分发处均在 wip/feat 分支待 Tony 确认并主干 |
