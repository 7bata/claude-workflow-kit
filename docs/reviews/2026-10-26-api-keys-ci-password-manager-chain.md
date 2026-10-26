# 评审链:项目 API key:CI 变量 + 团队密码管理器(公开 kit)

spec:`docs/superpowers/specs/2026-10-26-api-keys-ci-password-manager-design.md`。单元提交 3a3a2eb(autosquash 前 b6e6903,两轮修复 fb79572、767d887 已压进;实现模型 claude-sonnet-5-5;本会话由远程会话工具接管,写文件的单元用 Agent 工具派工,评审用 Workflow 只读跑)。

编排:轻量档(规则文本)——盲审 1 个 `opus` + `medium`;有 P0 / P1 修复后 1 轮 `opus` + `high` 裁决,上限 2 轮。开跑时 CPU 占用约 39%,可用内存 36%。

## 第 1 轮:盲审(2026-10-26,`opus` + `medium`,实际模型 claude-opus-5-5)

复核通过:中英两节位置与正文逐字一致、六条一一对应;模板与上线核对项标点对;两个插件 0.22.0;diff 新增行里内部名称 0 命中;与 README 六之四、七之五第 3 条、§五 不矛盾;模板 §5「从不提交 .env、真实凭据」与新 §6 一致。

- P1 两套模板 §3 第 5 条「改动影响到 .env.example 时,确认本地 .env 也同步过」与新 §6「本机开发不把真值写进 .env」冲突:照 §3 去同步会把新 key 的真值填进本地 .env。
- P1 spec 第 1 节说 Codex 版脚手架模板没有「密钥处理」一节,与事实不符:`plugins/workflow-codex/skills/scaffold/templates/AGENTS.md.tmpl` 第 108 行就是,内容仍是旧规则;合并后 Codex 版铺出的项目与 README 六之五冲突。
- P2 模板 §6 写成绝对的「不手贴」,丢了 README 第 2 条里旧 key 可以手贴的例外。

分流:有 P1、无 P0 → 修复后 1 轮裁决。修复(spec 第 9 节,提交 fb79572,实现模型 claude-sonnet-5-5):三套模板 §3 第 5 条改成「确认密码管理器里有对应条目、CI 变量已用同步命令写入;本地 .env 只同步非密钥配置」;Codex 模板 §6 / §3 / 上线核对同步,workflow-codex 0.19.0;三套模板 §6 补旧 key 例外。

## 第 2 轮:裁决(2026-10-26,`opus` + `high`,实际模型 claude-opus-5-5)

结论 PASS_WITH_NOTES。第 1 轮两条 P1、一条 P2 全部闭合,无推翻;AC1~AC4(含修订后的 AC2 / AC3)成立;两个插件 validate 通过,Codex 插件清单 JSON 合法;diff 新增行、未跟踪的 spec 与评审链、目标清单新增行对内部名称检索 0 命中;Codex 模板没有带进 Claude 专有工具名;「Codex 版与 Claude 版的口径差异」不加行判断正确;与六之四、模板 §5、gitignore、sop-generate 的测试账号用法不冲突。新 P2 四条,收尾处理:

- P2 三套模板 §6 把「CI 变量 + 密码管理器 + 运维登记处」套在所有真实值上,比 README 六之五 / 6e(只管第三方服务 API key)宽;§3 第 5 条「本地 .env 只同步非密钥配置」连本地开发库口令也不让进 .env → 收尾按 spec 第 10 节第 1、2 条改(限定第三方服务 API key;其余配置照常同步本地 .env)。
- P2 README 六之五 / 6e 末段用「仍是 / 照常」并点名 `# source:`,公开 kit 没定义过这个格式 → 收尾按 spec 第 10 节第 3 条改成「在它上方的注释里写…注释格式由团队自定」。
- P2 目标清单 2026-10-26 行的状态没跟上修订(未写 Codex 与 0.19.0)→ 收尾补。
- P2 spec 正文(第 1、4、5、6 节)没按第 9 节同步 → 第 9 节第 4 条改成「以本节为准」并列全。

收尾修复提交 767d887(`dev-toolkit:mechanical`,实现模型 claude-sonnet-5-5;三套模板 §6 限定第三方服务 API key、§3 第 5 条「其余配置照常同步本地 .env」、README 六之五 / 6e 不预设注释格式;validate 通过,内部名称 0 命中),spec 第 9 节第 4 条与新增第 10 节、目标清单行由主对话同步。

无 P0 / P1 未闭合,评审链到此结束(共 2 轮,轻量档上限内)。裁决模型:claude-opus-5-5;实现模型:claude-sonnet-5-5。
