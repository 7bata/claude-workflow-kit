# 评审链:开新项目加「非代码产出」类型(workflow / workflow-en 0.23.0,workflow-codex 0.20.0)

spec:`docs/superpowers/specs/2026-10-27-noncode-deliverable-project-type-design.md`。三个单元提交(分支 wip/noncode-project-type,基于 main 5cc9064):中文面 0ba92cb(`mechanical` + sonnet,实现模型 claude-sonnet-5-5)、英文面 f755f6a(general-purpose + sonnet,实现模型 claude-sonnet-5-5)、Codex 面 + PLAN / Progress f1681ba(`mechanical` + sonnet,实现模型 claude-sonnet-5-5)。编排:盲审 2 个 `opus` + `medium`(机器负载高改顺序跑;Workflow wf_3f97db97-487),有 P0 → 修复 → 续挖 1 轮 → 裁决。

## 第 1 轮:盲审(2026-10-27,`opus` + `medium` × 2,实际模型 claude-opus-5-5)

两份合并(按 file+line 归并;spec 第 42 行两份都报,严重度 P1 / P0 不同,标 conflict,按 P0 处理):

- **P0**(集成;忠实那份判 P1,conflict)spec:42 中文面提交 0ba92cb 随提交的 spec 第 3 节第 8 条带着内部工具包的本机绝对路径(含本机用户名与内部插件名),该提交已推到公开仓 wip 分支;工作树已改成「内部路径只写在派工简报里」但没提交。改后句子仍含一个内部概念字样(两份都报)。修法:squash 进 0ba92cb、autosquash 后 `--force-with-lease` 重推;旧对象在远端仍可按 sha 取到,是否进一步清理由维护者定。
- P2 scaffold SKILL(三面)步骤 2 新条的触发清单多了「方案」,步骤 3 第 0 条 / README 六之五 / Auto 模式 / hook 都没有,三面一致地不一致。
- P2 scaffold SKILL(zh / en)步骤 4 存在性检查循环与步骤 5 自检命令只覆盖代码项目路径,AGENTS.md 与 `材料/` 不在扫描范围(两份都报,措辞不同,归并一条)。
- P2 Codex PLAN 模板那一句差异(去掉 `.claude/CLAUDE.md`)没写进 spec 第 5 节。
- P2 docs/Progress.md:8 总览 Codex 行「同日加」会被读成 10-26。

复核通过(两份合并):README.zh-CN 六之五 / 步骤 2 / 步骤 3 与 spec 逐字一致;zh SKILL 新节位置与六处改动一致(全角标点);hook 半句一致;中文模板与内部底稿只差 spec 列的 5 处;zh / en 的 CLAUDE 与 AGENTS 模板 cmp 相同,Codex AGENTS 与 zh CLAUDE 相同、其余与 zh 相同;模板数 8 / 8 / 7;英文模板逐行对照行数、要点、占位符、表格列、硬规则条数相同;README 6e 与 en SKILL 要点数相同、固定译法贯彻;Codex 面只差 spec 第 5 节列出的那几点;三面对「什么时候走非代码产出分支」「落哪些文件」「每版怎么提交」答案一致;目录树四行、marketplace 两条描述、三个 plugin.json 版本、PLAN 索引行、Progress 两行与新条目互相一致;新增文字除 spec 第 42 行外内部词 0 命中。

分流:有 P0 → 修复后先 1 轮续挖再裁决。修复(spec 第 10 节,三个 `--squash` 提交,`mechanical` 子代理 + `model: sonnet`):spec 去路径与内部概念字样;三面步骤 2 触发清单去掉「方案」;三面步骤 4 / 5 补非代码清单与 AGENTS.md 扫描;spec 第 5 节补 PLAN 模板差异;Progress 日期写明。

修复(spec 第 10 节;三个 squash 提交 21de793 / 77aed15 / e92b67d,`mechanical` 子代理 + `model: sonnet`,实现模型 claude-sonnet-5-5):spec 去路径与内部概念字样(子代理顺手把第 10 节里主对话写的验收词表也改成了指向派工简报,公开仓不留那串词);三面步骤 2 触发清单去掉「方案」;三面步骤 4 / 5 补非代码清单(Codex 步骤 5 本来就扫 AGENTS.md,不加);spec 第 5 节补 PLAN 模板差异;Progress Codex 行日期写明。

## 第 2 轮:续挖(2026-10-27,`opus` + `medium`,实际模型 claude-opus-5-5;镜头 spec 验收覆盖 + 可执行性;Workflow wf_7c1b9daf-142)

闭合:P0(spec 全文内部词 0;第 3 节第 8 条已是「内部路径只写在派工简报里」);P2 三面步骤 2 清单无「方案」;P2 步骤 4 / 5 补句在、Codex 清单正确;P2 第 5 节补了 PLAN 差异。**未闭合**:P2 Progress Codex 行——前半句日期改对了,后半句「同日加的 API key 模板改动已撤回」现在接到 2026-10-27,日期错。无推翻。

- **P1**(边界)squash 提交 21de793 的说明正文含那个内部概念词,autosquash 后会进公开 main 的单元提交正文(已推到远端 wip 分支)→ 收尾时在重放单元提交那一步改写说明,再 `--force-with-lease` 重推。
- P2 Progress Codex 行「同日加的 API key…」→ 改「2026-10-26 加的」。
- P2 修复越界:三面「非代码产出分支」第 1 条「Intake 追问」的产出类别也被去掉了「方案」(修订 1 只要求改步骤 2 触发清单),与 spec 第 3 节第 1 条引文、REQUIREMENTS 模板「形式」列不一致 → 恢复。
- P2 `{{AUDIENCE}}` / `{{DELIVERABLES_BLOCK}}` 不在占位符替换表里、AUDIENCE 没有填不出的兜底,Auto 模式「留占位」会让步骤 5 自检报未替换 → 替换表补两行,Auto 条改「留替换表里的待补注释」。
- P2 步骤 5 非代码提交说明改写句放在代码块之后,`set -e` 代码块里写死的是代码项目的说明 → 挪到代码块前。
- P2 步骤 4「内容预填」没为非代码改写(DECISIONS 首条、REQUIREMENTS 节名、BUSINESS / MEETINGS 不生成)→ 加一条。
- P2 spec 第 10 节第 1 条前后两段逐字相同,读起来像没改 → 改措辞。

复核点:HEAD 新增行 grep 内部词除 spec 第 1 节泛称外 0;三面 CLAUDE / AGENTS 模板 cmp;PLAN 模板 Phase 0 标题与打 ✅ 规则对得上;Progress 模板首行「首次提交」/「Initial commit」与 SKILL 一致;Codex 步骤 3 第 0 条与规则片段自洽;hook 半句在;README 6e 与六之五要点相同、译法与 en 模板一致;spec 第 8 节验收通过。

分流:有 P1 → 修复后 1 轮裁决(spec 第 11 节,三个 `--squash`,`mechanical` 子代理 + `model: sonnet`;提交说明的词由主对话在收尾重放时改)。

修复(spec 第 11 节;三个 squash 提交 c4d066b / 714ca73 / 5585c5f,`mechanical` 子代理 + `model: sonnet`,实现模型 claude-sonnet-5-5):Progress 日期;三面恢复 Intake 产出类别;替换表补 `{{AUDIENCE}}` / `{{DELIVERABLES_BLOCK}}` 两行、Auto 条改措辞(Codex 规则片段没有对应半句,不改);步骤 5 提交说明句挪到代码块前;内容预填补非代码条;spec 第 10 节措辞。提交说明里的内部概念词由主对话在收尾重放单元提交时改掉。

## 第 3 轮:裁决(2026-10-27,`opus` + `high`,实际模型 claude-opus-5-5;镜头 回滚与可逆性 + 对抗反驳;Workflow wf_eff35a02-c15)

结论 **FAIL**。闭合:第 1 轮 P0(spec 文本干净;临时克隆里模拟 autosquash 能干净压回 3 个单元提交)、第 1 轮同处 P1、第 1 轮 4 条 P2、第 2 轮 5 条 P2。conflict 裁定:spec 第 42 行那条按 P0——公开仓已推送的提交里有含本机用户名与内部插件名的绝对路径,正落在「公开仓里出现内部实名」。**未闭合**:第 2 轮 P1——squash 提交 21de793 的说明含内部概念词,模拟 autosquash 确认会进中文面单元提交正文,改写还没做、没复核。无推翻。

- **P1**(回滚)三面 SKILL 步骤 5:非代码产出分支在已有材料的目录里铺设时,`git add -A` 会把目录里原有的大文件与含个人信息的文件放进首次提交,硬规则又要求立即 push,只能改写历史才能清;大文件检查只在之后每版提交前跑、且只扫 `材料/`。修法:首次提交只 add 落盘清单,add 前列出大文件与既有文件给用户;spec 第 7 节补一条。
- P2 大文件检查命令只扫 `材料/`,放在仓根或 docs/ 的大文件查不到 → 改扫全仓(排除 .git)。
- P2 没写误提交后怎么撤(未 push 用 `git rm --cached` + amend;已 push 要改写历史并通知协作者)。
- P2 `git push` 默认不推 tag,照规则 v1 / v2 只留本机;没有远端时 push 必失败没说。
- P2 版本日志「提交」列要填本版 sha 又要求提交后加行,每版多一处未提交改动 → 改成提交前加行、提交列填 tag 名(不打 tag 的先留空、提交后补短 sha 随下次提交带上)。
- P2 spec 第 9 节回滚:revert 会把版本号退回,应写明再升一个补丁号(临时克隆里实测倒序 revert 三个单元提交无冲突、diff 为空)。

复核点:远端 wip 分支与 HEAD 同为 5585c5f;全部提交说明 grep 内部名只有 21de793 命中;HEAD 新增行无实名;三组模板 cmp;修订 1、2 各条都在;hook 半句三面在;Progress 两行与 PLAN 索引;回滚路径可执行。

分流:有 P1 → 修复(spec 第 12 节,三个 `--squash`,`mechanical` 子代理 + `model: sonnet`)→ 主对话先 autosquash 并在重放单元提交时改写说明、`--force-with-lease` 重推 → 第 4 轮裁决看最终历史(链上限 4 轮,最后一轮)。

修复(spec 第 12 节;三个 squash 提交 5604c09 / e626da5 / 821c2ca,`mechanical` 子代理 + `model: sonnet`,实现模型 claude-sonnet-5-5):三面步骤 5 非代码首次提交只 add 落盘清单、add 前列大文件与既有文件;大文件命令改扫全仓(SKILL、模板、两份 README 共 14 处,旧命令只剩 spec 的历史引文);补撤销句、tag 推送句、版本日志改提交前加行且提交列填 tag 名;spec 第 7、9 节补句;三组模板 cmp 相同。随后主对话 autosquash、重放单元提交时改写说明(去内部概念词、加「裁决模型」行)、`--force-with-lease` 重推。
