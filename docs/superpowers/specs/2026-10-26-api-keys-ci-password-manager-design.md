# 项目 API key:CI 变量 + 团队密码管理器(小 spec)

日期:2026-10-26。出处:维护者 2026-10-26 拍板的六条规则,经另一个会话窗口转达本会话;原话见 `docs/REQUIREMENTS.md` 目标清单 2026-10-26 行。本仓是公开仓,规则按中性措辞写:不写内部工具名、账号、组织名、项目名、运维登记处的名字;具体工具与条目命名由团队自定。

## 1. 目标覆盖声明

覆盖目标清单 2026-10-26 那一行。不覆盖:内部工具包(同日有自己的实名版 spec,在内部仓库);维护者本机全局规则(由主对话在维护者点头后改);Codex 版插件(它的脚手架模板没有「密钥处理」一节,方法论 README 也没有对应小节,这次不加)。

## 2. Prior art

本仓现状:两套脚手架模板 `.claude/CLAUDE.md` §6「密钥处理」只有一句「真实值全部从 .env 读取,.env.example 用占位值」;README 中英的方法论正文没有「API key 的值从哪来、怎么进 CI」的规则。

## 3. 规则正文

### 中文 README(`README.zh-CN.md`,新小节「六之五」,放在「六之四、日志契约」之后、「七、主流程」之前)

### 六之五、项目 API key:CI 变量 + 团队密码管理器

项目用的第三方服务 API key(大模型、搜索、邮件等)按下面办:

1. **放哪**:一律放 CI 变量(masked + protected),不写 env 文件、不进仓库、不进文档。**值的唯一来源是团队密码管理器**:一把 key 一个条目,条目名写明厂商、账号与项目;备用 key 预先建成一池。会话只碰条目名,不把值读进对话;本机开发要真值时用密码管理器的 CLI 把值注入进程环境(如 1Password 的 `op run`),不把真值写进 `.env`。
2. **怎么写进 CI**:用「密码管理器 → CI 变量」的同步命令(读值、写变量,值不经对话、不回显),换 key、换账号也用它;不再手工粘贴。手贴只留给还没进密码管理器的旧 key,贴完补进去,之后按同步命令走。
3. **新项目要 key**:从备用池分配一把,密码管理器与厂商控制台两边改成项目名,再写进 CI;不让使用者自己去控制台建 key。
4. **没有 CI 的部署是例外**(单机 compose 的 env 文件、密钥文件、桌面机的环境变量):手改,改完在运维登记处记来源(在哪台机器的哪个文件或变量,备注写密码管理器条目名)。
5. **运维登记处**每把在用的 key 一行,备注写密码管理器条目名。
6. **不要求轮换日**:不给 key 设过期,规则与工具都不要求轮换日。

`.env.example` 仍是「这个项目用哪些 key」的声明:这类 key 照常列出,`# source:` 写密码管理器条目名并注明「用同步命令写入,不手贴」。工具名、条目命名与运维登记处由你的团队自定。

### 英文 README(`README.md`,新小节「6e」,放在「6d. Log contract」之后、「7. Main workflow」之前)

### 6e. Project API keys: CI variables + the team password manager

Third-party API keys a project uses (LLM, search, email, ...) are handled like this:

1. **Where they live**: always as CI variables (masked + protected) — never in env files, the repo, or docs. **The single source of truth is the team password manager**: one item per key, named with the provider, account and project; spare keys are pre-created as a pool. The session only touches item names and never reads values into the conversation; when local development needs a real value, inject it into the process environment with the password manager's CLI (such as 1Password's `op run`) instead of writing it into `.env`.
2. **How they get into CI**: with the "password manager → CI variable" sync command (reads the value, writes the variable; the value never passes through the conversation and is never echoed); use the same command to swap a key or move accounts. No more hand-pasting. Pasting is kept only for legacy keys not yet in the password manager — add them there right after, then use the sync command from then on.
3. **A new project needs a key**: assign one from the spare pool, rename it to the project on both sides (password manager and the provider console), then write it into CI; users do not create keys in the console themselves.
4. **Deployments without CI are the exception** (a single-machine compose env file, a secrets file, a desktop machine's environment variables): change them by hand, then record the source in the ops registry (which machine, which file or variable; note = the password-manager item name).
5. **The ops registry** has one row per key in use, with the password-manager item name in the note.
6. **No rotation deadline**: keys get no expiry, and neither the rules nor the tools require a rotation date.

`.env.example` remains the declaration of which keys the project uses: list these keys as usual, and in `# source:` write the password-manager item name plus "written by the sync command, not pasted". Tool names, item naming and the ops registry are up to your team.

### 两套脚手架模板 `.claude/CLAUDE.md` §6(整段替换;中文模板用全角标点,与该文件其余段落一致)

中文(`plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl`):

**绝不能写进 md 或代码的真实值**(API key、token、密码、加密 key 等)不入 git。部署环境的值放 CI 变量(masked + protected),值的唯一来源是团队密码管理器,用「密码管理器 → CI 变量」的同步命令写入、不手贴;本机开发要真值时用密码管理器的 CLI 注入进程环境(如 `op run`),不把真值写进 `.env`。`.env.example` 用占位值,并在注释里写值在密码管理器的条目名。没有 CI 的部署手改并在运维登记处记来源;每把在用的 key 在运维登记处有一行。

英文(`plugins/workflow-en/skills/scaffold/templates/CLAUDE.md.tmpl`):

**Real values that must never be written into md files or code** (API keys, tokens, passwords, encryption keys, etc.) never go into git. Values for deployed environments live in CI variables (masked + protected); the single source of truth is the team password manager, and they are written with the "password manager → CI variable" sync command, never pasted by hand. When local development needs a real value, inject it with the password manager's CLI (such as `op run`) instead of writing it into `.env`. `.env.example` uses placeholder values and names the password-manager item in a comment. Deployments without CI are changed by hand and their source is recorded in the ops registry; every key in use has a row there.

### 两套脚手架模板 `docs/DEPLOYMENT.md`「上线后核对」各加一条(放在清单末尾)

中文:`- [ ] 项目用的 API key 都在 CI 变量里(由同步命令从密码管理器写入,不在 env 文件里);每把 key 在运维登记处有一行,备注是密码管理器条目名`(全角标点)

英文:`- [ ] Every API key the project uses is a CI variable (written from the password manager by the sync command, not in an env file); each key has a row in the ops registry whose note is the password-manager item name`

## 4. 改动面(单元 U2,一个 `sonnet` + `medium` 实现 agent;都在本仓 worktree `.worktrees/wip-api-keys-rule`)

1. `README.zh-CN.md`:加「六之五」整节(第 3 节原文)。
2. `README.md`:加「6e」整节(第 3 节原文)。
3. `plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl` 与 `plugins/workflow-en/skills/scaffold/templates/CLAUDE.md.tmpl` 的 §6 正文整段替换(第 3 节原文;中文模板把半角「(),;」换成全角,保持一段)。
4. 两套 `templates/docs/DEPLOYMENT.md.tmpl`「上线后核对」末尾各加一条(第 3 节原文)。
5. `plugins/workflow/.claude-plugin/plugin.json` 与 `plugins/workflow-en/.claude-plugin/plugin.json`:`0.21.0` → `0.22.0`。
6. 其余不动:`.claude-plugin/marketplace.json` 描述、Codex 版插件、speak-human / send-to / ui-sweep。
7. 收尾自检:`claude plugin validate plugins/workflow` 与 `plugins/workflow-en` 通过;对改动的 diff 检索内部名称(内部域名、组名、账号名、内部项目名、内部工具名、运维系统名)0 命中。

## 5. 容易漏的输入与失败情形

1. 公开仓写进内部名称(内部工具名、组织名、项目名、运维系统名)——第 3 节全部用中性叫法,实现 agent 收尾 grep,评审再查一遍。
2. 英文版与中文版要素不对等(漏一条、多一条)——六条编号一一对应,评审逐条比。
3. 模板 §6 改完标点半角全角混用——中文模板按该文件习惯用全角;英文模板半角。
4. 只改了 README 没改模板、或只改了中文模板——改动面第 1~4 条都要做,评审对照清单。
5. 已检查,没有第五条。

都是规则文字,没有单元测试;由实现 agent 自检与评审覆盖。

## 6. 验收

- AC1 README 中英各多一节,六条编号对应、要素一致;位置在日志契约小节之后、主流程之前。
- AC2 两套模板 §6 与 DEPLOYMENT 核对项按第 3 节原文落下;中文模板全角标点。
- AC3 两个插件版本 0.22.0;`claude plugin validate` 通过。
- AC4 改动 diff 与本 spec、评审链、目标清单行里没有内部名称。

## 7. 回滚

`git revert -m 1` 合并提交;版本号不倒退(回滚后再升补丁号)。

## 8. 评审

轻量档(规则文本):1 个 `opus` + `medium` 盲审,镜头为正确性、中英一致、公开面无内部名称;有 P0 / P1 修复后 1 轮 `opus` + `high` 裁决。

## 9. 评审第 1 轮修订(2026-10-26)

盲审查出 P1 两条、P2 一条(链 `docs/reviews/2026-10-26-api-keys-ci-password-manager-chain.md`):两套模板 §3 第 5 条「改动影响到 .env.example 时确认本地 .env 也同步过」与新 §6「不把真值写进 .env」冲突;第 1 节说 Codex 版脚手架模板没有「密钥处理」一节与事实不符(`plugins/workflow-codex/skills/scaffold/templates/AGENTS.md.tmpl` 第 108 行就是);模板 §6 丢了 README 第 2 条里旧 key 可以手贴的例外。修订如下,第 1 节「不覆盖 Codex 版」作废,Codex 版纳入覆盖:

1. 三套模板(`plugins/workflow/…/CLAUDE.md.tmpl`、`plugins/workflow-en/…/CLAUDE.md.tmpl`、`plugins/workflow-codex/…/AGENTS.md.tmpl`)§3 第 5 条整行替换——zh:「5. 改动影响到 `.env.example` 时，确认密码管理器里有对应条目、CI 变量已用同步命令写入；本地 `.env`（不入 git）只同步非密钥配置」;en:「5. When a change affects `.env.example`, confirm the password manager has the matching item and the CI variable was written by the sync command; the local `.env` (not in git) is synced only for non-secret settings」。
2. 三套模板 §6 在「不手贴」后补旧 key 例外——zh 模板那句改为「……用「密码管理器 → CI 变量」的同步命令写入、不手贴（还没进密码管理器的旧 key 可先手贴，贴完补进去）；……」;en 模板那句改为「…written with the "password manager → CI variable" sync command, never pasted by hand (a legacy key not yet in the password manager may be pasted once, then added there). …」。Codex 模板 §6 整段替换为中文模板 §6 的同文(含这句例外)。
3. Codex 版的 `plugins/workflow-codex/skills/scaffold/templates/docs/DEPLOYMENT.md.tmpl`「上线后核对」末尾加中文那一条(第 3 节原文);`plugins/workflow-codex/.codex-plugin/plugin.json` 0.18.0 → 0.19.0。README「Codex 版与 Claude 版的口径差异」一节不加行:本条规则不分 Claude / Codex。
4. 第 1 节、第 4 节、第 5 节、第 6 节与本节不一致处以本节为准:Codex 版纳入覆盖(第 1 节「不覆盖 Codex 版」与第 4 节第 6 条「Codex 版插件不动」作废);改动面加 Codex 三个文件(`AGENTS.md.tmpl` §3 第 5 条与 §6、Codex `DEPLOYMENT.md.tmpl` 一条、`.codex-plugin/plugin.json` 0.19.0);AC2 加「Codex 模板 §3 第 5 条、§6、DEPLOYMENT 与中文模板同文」;AC3 加「workflow-codex 0.19.0」;第 5 节第 5 条改为「Codex 模板也有『密钥处理』一节——第 1 版 spec 漏看,修订 1 纳入」。

## 10. 评审第 2 轮(裁决)修订(2026-10-26)

裁决 PASS_WITH_NOTES(第 1 轮三条全部闭合),新 P2 四条,收尾改掉,以本节为准:

1. 三套模板 §6 的「CI 变量 + 密码管理器 + 运维登记处」规则套在了所有真实值上,比 README 六之五 / 6e(只管第三方服务 API key)宽——§6 整段改为:中文(workflow 与 Codex 两套同文)「**绝不能写进 md 或代码的真实值**（API key、token、密码、加密 key 等）不入 git，部署环境的值放 CI 变量（masked + protected）。其中第三方服务 API key 的值唯一来源是团队密码管理器，用「密码管理器 → CI 变量」的同步命令写入、不手贴（还没进密码管理器的旧 key 可先手贴，贴完补进去）；本机开发要真值时用密码管理器的 CLI 注入进程环境（如 `op run`），不把真值写进 `.env`；`.env.example` 用占位值，并在注释里写值在密码管理器的条目名；没有 CI 的部署手改并在运维登记处记来源；每把在用的 key 在运维登记处有一行。」;英文「**Real values that must never be written into md files or code** (API keys, tokens, passwords, encryption keys, etc.) never go into git; values for deployed environments live in CI variables (masked + protected). For third-party API keys the single source of truth is the team password manager: they are written with the "password manager → CI variable" sync command, never pasted by hand (a legacy key not yet in the password manager may be pasted once, then added there); when local development needs a real value, inject it with the password manager's CLI (such as `op run`) instead of writing it into `.env`; `.env.example` uses placeholder values and names the password-manager item in a comment; deployments without CI are changed by hand and their source is recorded in the ops registry; every key in use has a row there.」。
2. 三套模板 §3 第 5 条「本地 .env 只同步非密钥配置」连本地开发库口令也不让进 .env——改为:中文「5. 改动影响到 `.env.example` 时，第三方服务 API key 确认密码管理器里有对应条目、CI 变量已用同步命令写入；其余配置照常同步本地 `.env`（不入 git）」;英文「5. When a change affects `.env.example`, for third-party API keys confirm the password manager has the matching item and the CI variable was written by the sync command; other settings are synced to the local `.env` (not in git) as usual」。
3. README 六之五 / 6e 末段用了「仍是 / 照常」并点名 `# source:`,公开 kit 没定义过这个注释格式——中文改为「`.env.example` 是「这个项目用哪些 key」的声明:这类 key 照常列出,在它上方的注释里写密码管理器条目名并注明「用同步命令写入,不手贴」。工具名、条目命名、注释格式与运维登记处由你的团队自定。」;英文改为「`.env.example` is the declaration of which keys the project uses: list these keys as usual, and in the comment above each one write the password-manager item name plus "written by the sync command, not pasted". Tool names, item naming, the comment format and the ops registry are up to your team.」。第 3 节原文对应句以本条为准。
4. 目标清单 2026-10-26 行与本 spec 正文按修订同步(收尾由主对话做)。
