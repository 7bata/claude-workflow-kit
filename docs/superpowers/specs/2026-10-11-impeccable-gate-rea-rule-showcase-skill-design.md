# impeccable 机械闸门 + 展示型前端必调设计 skill + rea 一行规则 —— 设计

日期:2026-10-11。依据:调研报告 `docs/superpowers/research/2026-10-11-shaders-impeccable-rea-fit.md`;用户对报告的答复(目标清单 2026-10-11 两行):做 impeccable 与 rea,shaders 不做;新增「非管理后台类的前端(知识库对话页、艺术作品集站这类)直接调用设计 skill 来做,管理后台不调用」。

## 目标覆盖声明

- 覆盖:目标清单 2026-10-11「最近看到几个比较有意思的……」一行(采用项 1、2)与「1和2吧……」一行(展示型前端必调设计 skill)。
- 不覆盖:shaders(用户定不做);国内平台(抖音 / 小红书 / B 站 / 微博)的抓取与反自动化识别(本批只在对话里答复,是否另立调研等用户定);报告第七节顺带发现的其他缺口。

## Prior art

见调研报告第四、五节。impeccable(Apache-2.0,skill 4.5.2、引擎 0.1.14)是同类里唯一带确定性检测器的;rea(MIT,6.4.0)是逆向工具里覆盖面最广、对 Claude Code 最友好的;内部组件索引无同类组件。

## 一、规则改动(三条)

下面写的是本机全局规则(中文)的目标措辞;公开仓 README 中文面同义改写(不写本机路径,设计 skill 写成「impeccable,或 hallmark / frontend-design」),英文面按中文面翻译;脚手架模板与内部工具包按各自现有的压缩程度改写,要素不丢。

### A. 前端先分类:展示型前端的前端美术 stage 必须先调用设计 skill

1. **分类标准**(写在角色表「前端美术」行,一句):派工前先分类——**展示型前端**指面向外部用户的页面:作品集与艺术站、官网与落地页、知识库问答页、产品的用户端界面;**管理后台与内部工具界面**不算。拿不准按展示型处理。
2. **展示型前端的 stage prompt**(直通流程第 2 步,替换现有「前端视觉 stage(`opus`)的 prompt 先给设计方向(引用 hallmark / frontend-design skill)」那一句):stage prompt 第一步写明**先用 Skill 工具调用 `impeccable`**(本机已装为用户级 skill;新页面或整体改版走 `/impeccable shape` 再按它的 new-work 流程建立视觉方向,既有页面的打磨走 `/impeccable polish`,审查走 `/impeccable critique`;它第一步会跑自带的 `impeccable context` 命令读 PRODUCT.md / DESIGN.md),拿到方向后再动手;没装 impeccable 的机器用 hallmark / frontend-design。该项目第一次用时,由主对话(不是子代理)先跑一次 `/impeccable init` 写 PRODUCT.md——它会问几个产品问题,子代理无人可问。之后再点名本项目首轮产出里出现过的默认样式让它避开,清单以 `detect` 的套路类规则(cream-palette、italic-serif-display、numbered-section-labels、hero-eyebrow-chip、kicker-above-heading、overused-font)为准,逐轮补;「规则里不自己维护样式清单」不变。
3. **管理后台与内部工具界面**:不调用设计 skill,照现有做法按截图与反馈改;只走 B 的机械闸门。
4. 不装 impeccable 的 hook、不开 live 模式、critique 不进评审链(它强制拆两个子代理,与盲审编排是两套);hallmark 保留不删,规则点名 impeccable,若出现两个 skill 同时触发的噪音再去掉 hallmark。

### B. `detect` 机械闸门(所有前端单元,不分类型)

1. **评审链之前**(直通流程第 2 步「每单元完成即派评审链」之前加一句):前端单元的视觉 stage 返回后、开评审链之前,**由主对话(不是实现子代理)** 对该单元改过的 UI 源码目录跑 `npx impeccable@<锁定版本> detect --json <目录>`;退出码 2 且含**一眼可见类**规则(text-overflow、text-occlusion、low-contrast、broken-image、script-error、content-hidden-at-rest)的先退回修复再开评审;**套路类**(cream-palette 等)只把发现附进评审 prompt 当只读事实,不自动退回;退出码 0 不等于通过,评审链照开。detect 跑不起来(无网络、无引擎)时在评审 prompt 里写明「detect 未跑」,不许当作通过。
2. **截图交付预审之前**(截图交付规范「交付前先预审」那段加一句):派视觉评审子代理之前,主对话对要截图的本地地址(需要本机 Chrome)或构建出的 HTML 文件跑一次同样的 `detect --json`,输出文件与截图 HTML 放在一起存档,并作为只读事实交给视觉评审子代理;一眼可见类发现先修再截图。detect 是一次性命令,结束即退出,不留进程。
3. **环境**:本机 `~/.claude/settings.json` 的 env 加 `IMPECCABLE_NO_TELEMETRY=1`;规则里写「锁版本」,当前锁 4.5.2;艺术站先写 `detector.ignoreRules` 豁免清单再扫(放该项目 `.impeccable/config.json`)。
4. **硬闸门范围**以 U0 试点为准:一眼可见类规则里试点在已验收页面上误报为 0 的进硬闸门,其余降为「附进评审 prompt」。U0 结果出来前按上面六条写,出来后由主对话定稿。
5. 可选(本批不做,记录):档位表加一行「机械检测」(haiku + low + `dev-toolkit:mechanical`,只跑命令回传 JSON)。

### C. rea 一行规则

1. 「新产品/大功能先做 GitHub 调研」一节末尾加一段:调研或 spike 涉及分析 Electron/JS 打包产物、APK、闭源二进制时,实现者先用 rea 的 CLI 取只读静态证据(例如 `npx -y rea-agents@6.4.0 analyze-javascript-application <路径> --json`);默认不装它的 MCP(约 100 个工具、服务端无按需加载);确要装时按项目用 `claude mcp add` 手动注册,先 `npx rea-agents setup --dry-run` 看计划,不让它自动改 `~/.claude.json`;需要 Ghidra 时先问再装;用它的行为捕获(运行目标程序)必须在一次性账号或容器里、不带真实凭据的环境变量,并按「测试启动的进程测完即关」核对。它不做读进程内存取密钥、iOS 运行时 hook、风控对抗,这些仍走各项目既有路线。
2. 本机 `~/.claude/skills/github-research/SKILL.md`「快扫」一节末尾加一条:逆向类意图(弄清没有源码的 App / 网站 / 打包产物 / 二进制怎么工作)的已知工具是 rea,用法与边界按工作流规则的「GitHub 调研」一节;同类专用 MCP(Ghidra、IDA、JADX、mitmproxy 各一个)只在 rea 深度不够时补。

## 二、本机安装与试点(U0)

1. 安装:`npx impeccable@4.5.2 install --providers=claude --scope=global --no-hooks`,确认写入的只有 `~/.claude/skills/impeccable/`;安装前后比对 `~/.claude/settings.json` 与 `~/.claude.json`,除 env 那一行外不得有差异;不跑 `init`、不装 hook、不开 live。
2. 引擎:首次运行 `~/.claude/skills/impeccable/scripts/impeccable --version`(或 `doctor`)触发下载到 `~/.impeccable/bin/<版本>/`,确认 launcher 校验了 sha256;记录引擎版本。
3. env:`~/.claude/settings.json` 的 `env` 加 `IMPECCABLE_NO_TELEMETRY=1`,改前备份 `~/.claude/settings.json.bak-20261011-impeccable`。
4. 试点:对三个本机项目各跑一次 `detect --json`——录音转写产品的前端源码目录(React,已验收上线)、艺术作品集站(Astro,已发布;源码目录与构建出的 HTML 各一次,构建输出到 `/tmp` 下的目录,不动仓库)、短视频素材采集工具的后台前端(React,管理后台样本);若 URL 扫描可行,再对艺术作品集站起一次本地 dev server 扫一次 URL,启动前记 PID / 端口,扫完即关并核对。对每条发现读源码判断真假,产出**按规则分的命中数与误报数表**,并给出一眼可见类六条规则各自能不能进硬闸门的结论。三个仓库只读,不提交、不改文件。
5. 报告:上述全部写进 `docs/reviews/2026-10-11-impeccable-rea-showcase-chain.md` 的 U0 节(由主对话写入),数字留给 B.4 定稿。

## 三、同步面与单元划分

| 单元 | 面 | 档位 |
|---|---|---|
| U0 本机安装与试点 | `~/.claude/skills/impeccable/`、`~/.claude/settings.json`(env)、`~/.impeccable/`、三个项目只读 | sonnet + medium |
| U1 本机规则 | `~/.claude/CLAUDE.md`(A、B、C;改前备份 `~/.claude/CLAUDE.md.bak-20261011-impeccable-rea`)、`~/.claude/skills/github-research/SKILL.md`(C.2;改前备份同目录 `SKILL.md.bak-20261011-rea`) | sonnet + medium |
| U2 公开仓 | `README.zh-CN.md`、`README.md`(角色表前端美术行、直通流程第 2 步、门禁段的预审句、第八节)、`plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl` 与 `plugins/workflow-en/...` 第 124 行附近的前端视觉 stage 句与第 85 行门禁句、两个插件 `plugin.json` 版本 0.18.1 → 0.19.0、README 里引用版本号的地方 | sonnet + medium |
| U3 内部工具包 | `WORKFLOW.md`(三条全句)、核心 `stellark-workflow/SKILL.md`(见下)、`references/main-gate.md`(B.2)、`references/research.md`(C)、`references/review-chain.md`(B.1 的「detect 未跑不算通过」)、`references/upstream-map.md`、`stellark-parallel-do/SKILL.md` 第 11 行前端美术句、`stellark-scaffold` 的模板派工句;在该仓建 wip 分支提交并推送,`docs/Progress.md` 加条目 | sonnet + high |

U3 的核心 `SKILL.md` 有 token 上限(按该仓 `docs/reviews/2026-09-23-slim-c/c1-map.md` 的公式,现为 6499.57 / 6500):本批核心只加两处短入口——前端美术行加「展示型前端先调设计 skill」、七.4 派工句加「detect 闸门见 references/main-gate.md」——必须用别处等量压缩抵消,压缩只许丢日期、数字、与别处重复的字,「不许 / 禁止 / 必须 / 一律」与 `references/` 入口的出现次数前后相同;做不到无损就**停下报数字**(加了多少、差多少),入口先只放 WORKFLOW.md 与 references,由用户定是否放宽上限。替换清单用脚本套用(每条 old 恰好出现一次),套完核对字数。

每个单元的 FORBIDDEN FILES:不属于本单元那一列的任何文件;U0 不得改三个试点仓库的任何文件;U2 不得改 `docs/` 下除本 spec 以外的文件(Progress 与评审链由主对话写);U3 不得改公开仓。所有单元:绝不重启共享服务、绝不读写生产数据、禁止 force push 与丢弃改动的历史改写;启动的进程记 PID / 端口、测完即关并核对;并发前看 CPU 占用。

## 四、验收条款

1. 全局 CLAUDE.md 与 README 中英:角色表前端美术行含分类标准;直通流程第 2 步含「先用 Skill 工具调用 impeccable」「主对话先跑 /impeccable init」「管理后台不调用」「detect 闸门」「detect 未跑不算通过」;门禁 / 截图交付段含「detect 结果与截图 HTML 一起存档、交给视觉评审子代理」;第八节末含 rea 段落(CLI 取证据、不默认装 MCP、`claude mcp add`、Ghidra 先问、行为捕获隔离、不做的三件事)。`grep -c` 各关键词每个面 ≥ 1。
2. 两份模板:第 124 行附近的前端视觉 stage 句改成「先分类;展示型先调 impeccable(或 hallmark / frontend-design);管理后台不调」,门禁句含 detect;插件版本 0.19.0。
3. 本机:`~/.claude/skills/impeccable/SKILL.md` 存在;`~/.claude/settings.json` 的 hooks 段无 impeccable 条目、env 含 `IMPECCABLE_NO_TELEMETRY`;`~/.claude.json` 无变化;备份文件存在;`~/.impeccable/bin/` 下有引擎。
4. U0 试点表:三个项目各有按规则分的命中 / 误报数,一眼可见类六条规则各有结论;所有启动的进程已核对退出。
5. 内部工具包:WORKFLOW.md 三条全句到位;references 三个文件到位;核心 SKILL.md 字数 ≤ 6499.57 或原样未动并附数字报告;`references/upstream-map.md` 记了本批;wip 分支已推送。
6. 本机 github-research skill「快扫」末尾含 rea 一条,备份存在。

## 五、容易漏的输入与失败情形

1. **detect 跑不起来**(无网络下载不了引擎、机器没有 Chrome 扫不了 URL):使用者合理预期是闸门「没跑」而不是「通过」——规则写明记「detect 未跑」,目录 / HTML 扫描不需要 Chrome 可作退路。U0 核对 launcher 无网时的失败方式并写进报告;U1 / U2 措辞覆盖。
2. **艺术站刻意用的斜体衬线、米白背景触发套路类规则**:合理预期是不被自动退回——规则把套路类定为只附评审 prompt,并要求艺术站先写豁免清单。U0 在艺术作品集站上实测套路类命中数;U1 / U2 措辞覆盖。
3. **项目没有 PRODUCT.md 时子代理触发 `/impeccable init`**:init 会提问,子代理无人可答会卡住或编造——规则写明首次由主对话跑 init。U1 / U2 措辞覆盖;U0 确认 `impeccable context` 在没有 PRODUCT.md 的目录里的输出是提示而不是阻塞。
4. **并发实现子代理触发 impeccable 的编辑后 hook**:预期是不触发——本批不装 hook,U0 核对 settings.json 无 hook 条目。
5. **内部工具包核心 skill 超上限**:预期是不默默删要素——U3 做不到无损就停下报数字,评审核对禁令词与 references 入口次数前后相同。

## 六、评审

每单元盲审 2 个(opus + medium,镜头:正确性 / 边界与异常情形;核对测试本身的要求在这里对应核对验收条款逐条命中),脚本按 file + line 归并并标 conflict;有 P1 修复后裁决(opus + high);有 P0 修复后续挖再裁决。U0 的评审额外核对:安装没有写入 hook、settings.json 除 env 无差异、进程全部退出、试点数字有依据(发现条目能对上源码)。本批不触及规则 3 的不可逆操作。评审链记录:`docs/reviews/2026-10-11-impeccable-rea-showcase-chain.md`(内部工具包单元的细节记在该仓)。
