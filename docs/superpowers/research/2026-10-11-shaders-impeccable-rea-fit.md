# shaders / impeccable / rea 三个开源工具与本工作流的契合度调研

日期:2026-10-11。起因:用户点名三个仓库——前端设计相关的 shader-effects-inc/shaders、pbakaus/impeccable,逆向相关的 morluto/rea——认为「对我们是有需求的」,要求先读最近一个月的会话记录核实有没有真实需求,再看怎么融入工作流。

## 一、结论

1. **前端视觉需求是真的,但要的不是特效,是少返工。** 最近 31 天用户本人关于外观的反馈全是「排版、信息层级、配色收敛、手机版溢出、看截图说不好看」,没有一条要背景、光效、动效、氛围。同一块界面改三轮仍「说不上来哪里别扭」、配色「太花→太单调→柔和多色」三轮摆动、「这几个没改啊」这类返工才是成本所在;助手侧的截图视觉预审单个功能最多连开 5 轮。
2. **impeccable 只有一块独有价值:59 条无需模型的确定性检测规则(`npx impeccable detect`)。** 它能机械地抓文字溢出、遮挡、低对比度、破图、脚本报错,退出码可判,正好对着上面的返工点。它的 skill 本体与已装的 hallmark 高度重叠(hallmark 这个月一次都没被调用),hook 与 live 模式和本工作流的进程纪律冲突。推荐:只把 `detect` 当机械闸门接进截图交付预审与评审链前,不装 skill、不装 hook、不开 live。
3. **shaders 这个月没有任何需求证据。** 36 条外观反馈里 35 条判「shaders 帮不上」,艺术作品集站的要求也只是内容摆放和尺寸。它是 WebGPU 专用、无 WebGL 回退、默认开 5% 遥测、MCP 要账号、预设库要付费,公开仓才 12 天只有 1 个提交。推荐:现在不进工作流,记为展示型站点的素材库候选,等有项目真要氛围背景时再按约束用。
4. **逆向需求有,但窄,而且最难的部分 rea 不覆盖。** 真实的逆向工作只在两个项目:微信 macOS 4.x 本地库导出(密钥在进程内存,靠主动捕获取;rea 没有读进程内存、没有 SQLCipher、没有 Frida)和小红书接口风控探测(最后是移植开源签名算法;rea 的 JS 静态分析能帮着定位签名函数,帮不上风控对抗)。rea 最强的是 Electron/JS 打包产物静态分析(零额外安装),其次 APK(要 JADX+JDK)和原生二进制(要 Ghidra 或付费的 Hopper)。推荐:不全局装它那约 100 个工具的 MCP;在「GitHub 调研」一节加一行——涉及闭源 JS/Electron/APK/二进制时先用 rea 的 CLI 取只读证据,MCP 只按项目用 `claude mcp add` 手动挂。

## 二、方法与规模

- 会话语料:`~/.claude/projects` 下最近 31 天(2026-09-10 至 2026-10-11)修改过、大于 20KB 的会话文件 1031 份,提取用户侧文本消息 2766 条(含大量自动脚本、技能正文注入、跨会话转达,判定员逐条区分)、Skill 调用 233 次、子代理与 Workflow 派工行 1587 行。
- 判定:26 个 sonnet + medium 子代理,并发 4(当时 CPU 占用约 80%,按规则减半)。其中 19 个逐份读完全部原话(每份约 120KB)、按需打开原始会话查上下文(共 30 次);3 个各读一个仓库的本地只读克隆;1 个收集助手侧旁证(Workflow 脚本里的前端美术 stage、各仓 git log 外观类提交、进度文件里的预审轮次、相关记忆);3 个做同类替代品快扫(`gh search repos` + 仓库元数据)。
- 内部组件索引(GitHub 调研第 0 步):核对过,没有设计、特效、逆向类组件(只有一条逆向过语音合成 WebSocket 协议的客户端和几条爬虫),无内部候选。
- 排除:本次请求那条消息本身;`-private-tmp-*` 目录下的自动验收会话。

## 三、需求证据

### A. 前端视觉

| 指标 | 数字 |
|---|---|
| 判定为外观类的用户原话(含「可能」级) | 36 条 |
| 其中要背景 / 光效 / 动效 / 氛围的 | 0 条 |
| 类型分布 | 看截图后的反馈 12、整体方向 11、排版间距 10、手机版 2、其他 1 |
| shaders 能帮上 | 否 35、可能 1 |
| impeccable 能帮上 | 是 5、可能 26、否 5 |
| 这个月 hallmark / frontend-design 两个设计 skill 被调用次数 | 0(233 次 Skill 调用里) |
| Workflow 脚本里真正的前端美术 stage | 16 处,9 个项目(录音转写产品、小红书热点工具、需求访谈工具、内部记账系统、艺术作品集站、短视频采集工具、餐厅管理后台、报价提案文档、内部项目管理系统) |
| 各仓外观类提交占比(上限估计) | 约 8%(1589 个提交里约 132 个;正则含「首页」「截图」,把文档提交也算进去了) |

典型原话(用户本人):

- 录音转写产品,同一块界面三轮:「这部分的 ui 我还是觉得不太好看,能不能再改一下」「还是不好看,就是这个总是感觉特别别扭,我也说不上来」「A,但是这个小字不用显示」。
- 录音转写产品:内测用户说不够简洁、想要 ChatGPT 那种界面,用户认同;助手出 A/B/C 三版 HTML 样稿,用户看过后一次选定 B。
- 内部项目管理系统纯前端 demo:「这个太丑了……整体来说还是不错的,细节上可能稍微差一点,需要再打磨」;配色三轮:「有点太花花绿绿了」→「这次又有点太单调了」→「柔和多色吧」。
- 个人 PWA 产品手机主屏:「这块距离没弄好,太窄了」「顶部这里太丑了」「又啰嗦而且间距也不对」,同一区域至少两轮。
- 录音转写产品:「这几个没改啊」(上一轮截图反馈没改到位)。
- 内部记账系统:视觉设计明确交给设计师同事,「先实现功能再说」。
- 内部项目管理系统、短视频采集工具的多数「看截图后反馈」是砍字段、页面太长、入口不显眼——信息取舍,不是风格。

助手侧成本:截图视觉预审在录音转写产品一个功能上连开第 3、4、5 轮复审;艺术作品集站每批 30~44 张截图、预审 2~3 轮,一个批次子代理约 126 万 token,其中截图相关约 38 万;整页截图懒加载空白被当缺陷多花过一轮。记忆里用户明确说过评审票核不到观感、最后一道闸是主对话自己看图。

### B. 逆向

| 指标 | 数字 |
|---|---|
| 判定为逆向类的用户原话(含「可能」级) | 9 条 |
| rea 能帮上 | 是 1、可能 8 |
| 目标类型 | 网站未公开接口 5、微信本地库 3、其他 1 |
| 真实做过逆向工作的项目 | 2 个 |

两个真实案例:

- 微信知识库项目:微信 4.1.11 把密钥移出明文内存,被动扫描失效,改用开源工具主动捕获取密钥,再手写 SQLCipher-4 解密全库(197 个会话、128578 条消息);公众号文章靠手写采集脚本,按最终跳转地址识别人机验证页。用户原话里是「把工作微信里的所有数据都导出」「聊天记录里的文件能读取到吗」,没有提逆向,是复用已有的微信适配器。
- 小红书热点工具:对 App 端热搜接口做变体探测,证明 shield 与设备参数绑定、旧设备身份被投喂冻结的假榜单;Web 端没有自己逆向,移植开源的 x-s 签名实现到 Go,决策记录写明「避免从零逆向摸索耗费大量时间」。用户原话:「话说小红书有客户端吗,能不能 hook 一下,类似〔微信适配器〕」——这是唯一一条判「rea 能帮上」的。
- 短视频采集工具的 Instagram / TikTok 问题是账号被判自动化、无头浏览器被识别,属于采集运维,rea 帮不上。

## 四、三个仓库的事实

### shaders(shader-effects-inc/shaders,npm `shaders` v4.0.4)

- 是什么:WebGPU 声明式着色器组件库,200 个免费效果(渐变、噪声、玻璃、光效、过渡、鼠标轨迹),React / Vue / Svelte / Solid / 原生 JS 同一套 API;MIT。另有 Pro(1000+ 预设、55+ 网站区块、无水印渲染)。
- 给代理用的面:skill(SKILL.md 约 14.7KB + 组件目录 22.8KB,粗估 1 万 token 量级,SKILL.md 约 4k)、远程 HTTP MCP(`https://shaders.com/mcp`,要账号 OAuth,免费账号可连)、CLI(`connect` 会装依赖、写配置、浏览器登录、装 skill)。
- 硬约束:WebGPU 专用,没有 WebGL 回退(源码头注释写明),不可用时画布透明、控制台静默,要自己在 `onUnavailable` 回调里换 CSS 渐变或静态图;运行时遥测默认开(5% 抽样上报 shaders.com,`disableTelemetry` 可关);没有 Astro 官方集成(可走 JS 入口);SSR 安全。
- 成熟度:公开仓 2026-09-29 新建,只有 1 个提交,CHANGELOG 的比较链接从 v3.2.475 起,说明是私有老版本公开;10 天内发 5 个版本,API 可能还在变;484 个测试文件,未见视觉回归。
- 栈匹配:本机项目多是 React + Vite 的后台工具界面(用不上),艺术作品集站是 Astro + GSAP(最可能用,但这个月没要过氛围效果)。

### impeccable(pbakaus/impeccable,skill 4.5.2,引擎 0.1.14)

- 是什么:一个 skill(24 个子命令:polish / critique / audit / animate / typeset / layout / harden / adapt……)+ Rust 引擎二进制 + 59 条确定性检测规则 + 编辑后 hook + live 浏览器变体模式 + Chrome 扩展;Apache-2.0,无付费层。
- 检测器(`npx impeccable detect <目录|HTML|URL> --json`):无需模型和 API key;退出码 0 无主要发现、2 有、1 扫不了;扫 URL 要本机 Chrome。规则里「一眼可见」类:text-overflow、text-occlusion、low-contrast、broken-image、script-error、content-hidden-at-rest、tiny-text;「AI 套路」类:cream-palette、italic-serif-display、numbered-section-labels、hero-eyebrow-chip、kicker-above-heading、overused-font(Inter / Roboto / Fraunces / Geist / Space Grotesk)——与本工作流派工 prompt 里手写的「避开默认样式清单」一一对应;另有 design-system-* 规则读根目录 DESIGN.md 的 frontmatter 做漂移检查。
- 安装落点:`npx impeccable install --providers=claude --scope=project|global` 写 `.claude/skills/impeccable/`(或 `~/.claude/skills/`)与项目 `.claude/settings.local.json` 的 hook;也可作插件装。引擎首次运行从 GitHub Releases 下载到 `~/.impeccable/bin/`,带 sha256 校验,skill 包另有 Ed25519 签名。不改 CLAUDE.md、不改 `~/.claude.json`(只读代码推断,未运行验证)。
- 与现有的重叠:hallmark(已装,67KB 约 19k token,这个月零调用)和 frontend-design 插件都是审美指引,没有机械检查;impeccable 的 skill 覆盖 frontend-design 全部内容,与 hallmark 大部分重叠;两个都装会同时触发、token 相加。impeccable 独有的只有检测器、live 模式和 Operate 受众模式(对后台系统有针对性)。
- 风险:hook 在每次 Edit/Write 后和 Stop 时跑,独立于模型工具审批,首次编辑就可能在后台联网下载引擎(README 明文警告),并发实现子代理也会触发、检测提醒会注入它们的上下文;live 模式向本地 dev server 注入脚本、起常驻 helper、接受变体时写回源码并以用户权限跑 package.json 里的脚本,与「测试进程测完即关」冲突;概念骰子功能会把选择结果 POST 回 impeccable.style、另有版本检查(`IMPECCABLE_NO_TELEMETRY` / `DO_NOT_TRACK` 可关);规则偏「反 AI 审美」,对艺术站刻意用的斜体衬线、米白背景会误报,要写豁免清单;critique 命令强制拆两个子代理,与本工作流的盲审编排是两套;近 30 天 100+ 次提交、引擎 0.1.x 仍在重写期,锁版本再用。
- 常驻成本:skill 正文约 3.5k token;单个命令 1.5~2k;critique 约 12k、new-work 约 16k。只用 CLI 则零常驻。

### rea(morluto/rea,npm `rea-agents` 6.4.0)

- 是什么:把 Hopper / Ghidra / IDA、JADX、Chrome CDP、HAR 解析、Electron/JS 静态分析等本地引擎包成约 100~104 个 MCP 工具 + 同能力的 CLI + 一份路由 skill(14KB + 六个参考文件);MIT;全程本地,未发现遥测代码;不需要账号。
- 各类目标在 macOS 上的要求:Electron/JS 打包产物与 .asar——只要 Node,零额外安装;网站观察——Chrome(会丢弃 Cookie 与 Authorization 头);HAR——离线;原生二进制——Hopper(付费,首次启动要在图形会话里点一次)或 Ghidra(免费,要 JDK)或 IDA;APK——无界面 JADX + 完整 JDK;Apple 应用包清单与签名元数据——静态可读;运行目标做行为捕获——以当前用户权限、继承环境变量,官方明说不是沙箱;mitmproxy 原生流只支持 Linux。
- 不做的事(恰是本机最可能遇到的):读进程内存取密钥、SQLCipher 解密、Frida / 调试器附加、iOS 运行时 hook、脱壳、绕证书固定、风控对抗。
- 安装落点:`npx rea-agents setup --client claude_code`(可 `--dry-run`)写用户级 `~/.claude.json` 的 `mcpServers.rea`(MCP 版本钉死)与 `~/.claude/skills/reverse-engineer-anything/`,备份 `.rea.backup`;不改 settings.json、CLAUDE.md、不加 hook。与本机「MCP 注册用 `claude mcp add`」的教训有张力,可手动注册。
- 上下文成本:tools/list 恒定返回全部工具,服务端没有按需加载开关;单个工具完整 schema 可达约 15KB,仓库自带 `REA_MCP_INPUT_SCHEMA_PROFILE=compact` 把每个限到 13KB 内;Claude Code 的延迟加载能缓解,未实测。
- 成熟度:2026-04-14 建仓,35 个 Release,861 个测试文件,真实工具链验证脚本,当天开当天关的 issue 很多;9.5 万 star 对半年的仓偏高,不能当成熟度依据。

## 五、同类替代品快扫

- 设计 skill:impeccable 是同类里唯一带确定性检测器的;hallmark(Nutlope/hallmark,2.99 万 star,最近推送 2026-08-06)已装未用;taste-skill(9.5 万)、ui-ux-pro-max(13.5 万,风格与配色素材库)是品味提示或素材库,不能替代检测器;open-design 是桌面应用,不在一个层级。没有更合适的替代。
- 着色器库:paper-design/shaders(3588 star,Apache-2.0,零依赖,2026-10-11 仍在推送)是最接近的对手,但没有官方 skill / MCP;其余候选太小或无 license。若要用,shaders 是对代理最友好的,paper-design 作备选。
- 逆向:单项更深的专用 MCP 有 LaurieWired/GhidraMCP(1.1 万)、mrexodia/ida-pro-mcp(1.26 万)、zinja-coder/jadx-mcp-server(794)、snapspecter/mitmproxy-mcp(125);frida 方向最高星的一年多没动。rea 覆盖面最广,适合做统一入口,专项深度不够时再补专用的。

## 六、融入位置候选与推荐

### impeccable(推荐做,先试点误报)

1. **最小接入(推荐)**:只用 CLI。
   - 截图交付规范的预审段:派视觉评审子代理之前,主对话对本地 dev server 地址或构建出的 HTML 跑一次 `npx impeccable@<锁定版本> detect --json`,结果文件与截图 HTML 一起存档,喂给视觉评审子代理当只读事实;一次性命令,结束即退出,不留进程。
   - 直通流程第 2 步前端视觉 stage 返回后、开评审链之前:主对话(不是实现子代理)对该单元改过的 UI 源码目录跑 `detect --json`;退出码 2 且含 text-overflow / text-occlusion / low-contrast / broken-image / script-error 的先退回修复再开评审;AI 套路类只记入评审 prompt,不自动退回。
   - 派工 prompt 里「点名要避开的默认样式清单」旁加一句以 detect 的套路类规则为准,减少逐轮手补清单;「规则里不自己维护样式清单」原则不变。
   - 可选:档位表加一行「机械检测」,haiku + low + `dev-toolkit:mechanical` 只跑命令回传 JSON,prompt 写明禁止 install / update / live、禁止改 `.impeccable/` 配置。
   - 环境统一设 `IMPECCABLE_NO_TELEMETRY=1`;版本锁定;对艺术站先写 `detector.ignoreRules` 豁免清单再扫。
   - **前置试点**:在隔离目录用 `IMPECCABLE_BIN` 指向下载并核过哈希的引擎,对录音转写产品的前端源码和艺术作品集站各跑一次 `detect --json`,统计误报;这两个数字决定上面两条能不能做成硬闸门。
2. **不做**:不装 skill(与 hallmark 重叠、常驻 3.5k+ token)、不装 hook(后台联网下载、干扰并发实现子代理)、不开 live、critique 不进评审链。

### rea(推荐做一行规则,不装 MCP)

- 「新产品/大功能先做 GitHub 调研」一节后加一行:调研或 spike 涉及分析 Electron/JS 打包产物、APK、闭源二进制时,实现者先用 `npx -y rea-agents@<锁定版本> analyze-javascript-application <路径> --json` 这类 CLI 取只读静态证据;默认不装 MCP,确要装时按项目 `claude mcp add` 手动注册(先 `setup --dry-run` 看计划),不让它改 `~/.claude.json`;需要 Ghidra 时先问再装;用行为捕获必须在一次性账号或容器里跑、不带真实凭据环境变量,并按「测试启动的进程测完即关」核对。
- 本机 github-research skill 的参考里记一条:逆向类意图的已知工具是 rea(不取进程内存、iOS 弱、约 100 个工具)。
- 微信数据库导出沿用既有路线,rea 只作读微信二进制的辅助 spike。
- 不动评审链与档位表;逆向类单元是否按规则 3 升档看是否触及不可逆操作,不因用 rea 而升档。

### shaders(推荐现在不做)

- 不加规则、不装 skill / MCP。本报告作为记录:展示型站点(作品集、官网首页)要氛围背景、光效、过渡时,前端美术 stage 可选用它,约束是必须写 `onUnavailable` 回退、关 `disableTelemetry`、颜色不从它配方的默认紫/深蓝渐变里取、先在一个站试点看包体积与低端设备表现。无头 Chrome 截图可能没有 GPU 而得到透明画布,预审要能区分回退路径与真缺陷。

## 七、顺带发现的更大缺口(不在本次范围,只记录)

逐份判定时顺手记的、反复出现但现有流程没工具的需求,按出现项目数排:带登录态的真浏览器抓取与反自动化识别(短视频采集、微信知识库、艺术作品集站三个项目反复卡住);按项目看 LLM 调用花费;测试与验收进程要人提醒才关;终端与远端中枢之间的权限确认不同步;对外文档(提案书、分工说明)缺模板;前端迭代时用户两次主动要多版 HTML 样稿并排看、看后一次选定——多方案并排预览可以成为前端美术 stage 的默认步骤。

## 八、待定

采用哪几项(impeccable 的 detect 闸门与前置试点、rea 的一行规则、shaders 不做),由用户定。定了之后按直通流程写小 spec 实现,同步面按「改工作流规则要同步的面」清单列(本机全局规则、本仓 README 中英与模板、内部工具包、本机 github-research skill)。

## 附:证据位置

- 子代理原始返回:本机会话目录下 Workflow `wf_b878b052-bbe` 的 `journal.jsonl`(26 条 result)。
- 语料提取脚本与分片:本机 `/tmp/history-scan/`(临时,不入库)。
- 三个仓库的只读克隆:本机 `/tmp/research-shaders`、`/tmp/research-impeccable`、`/tmp/research-rea`(临时)。
