# Decision Log — claude-workflow-kit

> 条目格式:`## 日期 - 类型(域): 标题` + What/Why/Changes,最新在上。由 `docs/DECISIONS.inbox.md` 的问答草稿消化而来;日常小决定与过程性确认不进本表。

## 2026-09-22 - process(review): 评审编排改为「盲审起步 + 接力续挖 + 裁决收尾」;换代后第一批实现做起跑档对照实验

- **What**:评审不再平行投票,也不是纯链式:首轮 2 个(高风险单元 3 个)互不可见的盲审平行发现、不数票、脚本按 file+line 归并并标 conflict;之后每轮一个 agent 带前面各轮全部发现、先推翻再找漏、换没用过的镜头;链末裁决轮 opus+high,盲审与续挖 medium;分流表与 4 轮上限;修复在评审 stage 外做,链状态落 `docs/reviews/<单元>-chain.md`。同日拍板:Opus 5.5 换代后第一批实现做分组对照(一半 sonnet+high、一半 opus+medium),按组比退回率与 token 再改档位表,实验前起跑档不动。
- **Why**:Tony 先要"一个 agent 评审完、下一个带着前一个的问题继续挖,而不是投票",再问能否同时避开链式(锚定、首轮跑偏)与投票(重复、不能翻案、数票)的短板;三个候选(A 盲审起步 + 接力续挖 / B 每轮先盲后看 / C 纯链式 + 对抗立场)选 A——独立只用于发现,继承只用于深挖与翻案,全程不数票。起跑档:换代前两个项目退回率 46% / 83% 超过规则 4 的 30% 线,但旧数据不跨代比较,所以用一次对照实验产生 5.5 时代的数据。
- **Changes**:README zh/en 二/三/七节、workflow/-en/codex 三份脚手架模板、codex parallel-do §6(kit 0.13.0);镜像到全局 CLAUDE.md、dev-toolkit、huake 两个 engineer 插件。见 Progress 2026-09-22。

## 2026-09-19 - process(workflow): omitClaudeMd 只用在纯机械 stage;AGENTS.md 本批不做

- **What**:`mechanical` 子代理类型(`omitClaudeMd: true`)只用于定位/清单/盘点与批量迁移/重命名/模板化改码两类纯机械 stage,常规实现与全部评审照旧加载 CLAUDE.md;scaffold 本批不生成 AGENTS.md。
- **Why**:省 token 只在不需要项目约定的机械活上安全;评审与实现依赖 CLAUDE.md 的硬规则。AGENTS.md 三种形态(指向 CLAUDE.md / 双份同步 / 按需生成)当时都没有明确需求,按 YAGNI 不做。
- **Changes**:workflow/-en 0.12.0(mechanical agent + 并发上限文档)。见 Progress 2026-09-19。
