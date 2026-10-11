# 评审链:impeccable 机械闸门 + 展示型前端必调设计 skill + rea 一行规则

spec:`docs/superpowers/specs/2026-10-11-impeccable-gate-rea-rule-showcase-skill-design.md`。单元:U0 本机安装与 detect 试点、U1 本机规则、U2 公开仓、U3 内部工具包(该仓的细节记在它自己的 docs/reviews 同名文件)。实现全部 sonnet(U0/U1/U2 medium,U3 high);评审盲审 opus medium,裁决 opus high。

## 第 1 轮:盲审(每单元 2 个,镜头 A 正确性 / 镜头 B 边界与异常)

### U0 本机安装与 detect 试点

试点数据(全部只读,三个仓库 git status 为 0 改动;启动的 preview 服务与 Chrome 已核对退出):

| 目标 | 扫法 | 退出码 | 命中 | 判定 |
|---|---|---|---|---|
| 录音转写产品 前端源码目录 | 源码 | 2 | broken-image 8、side-tab 4 | broken-image 8/8 误报(7 条在测试文件字符串、1 条在注释);side-tab 是有意设计的引用块左边线 |
| 短视频素材采集工具 后台前端源码目录 | 源码 | 2 | broken-image 1、side-tab 3、border-accent-on-rounded 1 | broken-image 误报(无 src 占位图);其余套路类、有意 |
| 艺术作品集站 源码目录 | 源码 | 2 | broken-image 1 | 误报(灯箱图 src 运行时赋值);.astro 基本扫不出东西 |
| 艺术作品集站 构建后 18 页静态 HTML | 静态 HTML | 2 | 105(cramped-padding 39、low-contrast 28、broken-image 18、hero-eyebrow-chip 9、tight-leading 9、其他 2) | broken-image 18/18 同一灯箱图重复;low-contrast 已复核的 13 条里 12 条是背景推断错误(另 15 条在 4 个未复核的子页,第 2 轮补扫);cramped-padding 全是 dialog 与列表的有意版式 |
| 艺术作品集站 渲染扫描 4 页(首页、writing、curating、community) | 渲染(本机 Chrome,单页约 10 秒) | 2/0/2/0 | hero-eyebrow-chip 1、low-contrast 1 | 都是真实命中;low-contrast 是图注 #9a978f 在 #f3f2ef 上 2.6:1,是否有意要人定 |

另核:没有 PRODUCT.md 的目录里 `impeccable context` 退出码 0、只给提示不阻塞(新建 / 改版类会要求先 init);无网下不到引擎时 launcher 退出码 127 并提示;本机 node 22.17.1 低于包要求 22.18.0,有警告但能用;安装器除 skill 目录外还写了 `~/.claude/agents/impeccable-*.md` 4 个子代理文件(首轮被移走,见发现 3)。

发现:
1. P1(镜头 A、B 同报)spec 第二节第 2 步与验收条款 3 写的「下载到 ~/.impeccable/bin/、launcher 校验 sha256」在本机不成立:引擎随安装器放在 skill 目录 `scripts/bin/darwin-arm64/`,launcher 对已在缓存或同级的引擎不校验。两位评审各自对照官方 engine-v0.1.14 的校验文件核过本机引擎哈希一致(第 2 轮记全 64 位)。处理:spec 已改写,第 2 轮 U0 复核并把数值记进本文件。
2. P1(镜头 A、B 同报,跨单元)已写进全局规则 / README 的 B.1 对「源码目录」扫描硬退回,按试点数据会把已验收的前端单元无端退回。处理:spec B 已定稿——只有渲染扫描进硬闸门,源码 / 静态 HTML 扫描只附评审 prompt;U1 / U2 / U3 第 2 轮改措辞。
3. P1(镜头 B)首轮移走的 4 个子代理文件被 new-work 流程收尾(finish-reviewer)用到,而规则 A 正要求新页面走 new-work。处理:放回,spec 第二节第 1 步改为「保留」。
4. P1(镜头 B)静态 HTML 的 low-contrast「27 条误报」里 15 条落在 4 个没做渲染复核的子页,结论无依据,其中至少一条与已确认的真实命中相同。处理:第 2 轮补扫这 4 页并改数字。
5. P2 录音转写产品 broken-image 分项算术(应为 7 + 1);没有 Chrome 时渲染扫描的退出码与输出未核;镜头 A 指出实现者对硬闸门的结论前后不一(verdict 全判不可、notes 又建议放两条)——由主对话定稿(见 spec B.0 / B.4)。

### U1 本机规则

无 P0 / P1(跨单元的 B.1 措辞问题见 U0 发现 2)。P2:「只走下面的 detect 闸门」方向词写反(闸门在同段前面);截图预审段没写「detect 未跑」的处理;避开清单旧例子与 detect 规则名并存、以哪份为准读不出;硬闸门六条写成定稿口吻没标待定;触发点写「视觉 stage 返回后」会让没有视觉 stage 的管理后台单元漏跑(spec 带来的歧义,已改为「实现返回后」);实现者的关键词 grep 按行计数只能证明有词、不能证明要素齐(评审已人工逐项核过,六项都在)。全部在第 2 轮一并改。

### U2 公开仓

P1(镜头 A、B 同报):README 中英与两份模板都没写「艺术站先写 detector.ignoreRules 豁免清单再扫」(spec B.3 与第五节第 2 条点名)。P2:门禁段写「跑一次同样的 detect」但命令要到后文才定义、没写完整命令与锁版本;避开清单的例子与 detect 规则名对不上;rea 段放在「定期校对」条之前、不在第八节末尾;模板漏「拿不准按展示型处理」;没提 critique;A.4 的「不装 hook、不开 live、critique 不进评审链」没写进 README;模板没写 impeccable 前缀与锁版本;实现者的校验没加 --strict(评审补跑三项通过)。分流:修复后裁决。

### U3 内部工具包

P1(镜头 B)两条:为抵核心 skill 的字数,压缩了 `[^orch]` 脚注(把已取消的「按链撤方」写成现行规则,且该脚注是登记的逐字保护段)和「取证前置(硬规则)」里的 token 预算(同为保护段、是派工要素)。P2:upstream-map 记了一处并没发生的压缩;核心入口「见 main-gate.md」指错(评审链前闸门正文在 review-chain.md,且少了 references/ 前缀);规则 A 在 skill 这一面只有 WORKFLOW.md 一处落点、核心七.4 仍是旧句(符合 spec 的上限约束,交主对话);内部脚手架模板比公开模板少 init、「拿不准按展示型」与门禁 detect 句;§五.2 与 main-gate.md 的「同样的 detect」没有前文;WORKFLOW.md 缺「hallmark 保留、双触发再去掉」一句;一处「。 →」标点。分流:修复后裁决。细节与第 2 轮记录在该仓同名文件。

### 分流

U0、U2、U3 有 P1 → 修复后裁决;U1 只有 P2,但要承接跨单元的 B 定稿改动,一并修复后进同一轮裁决。修复各派一个 sonnet 实现 agent(U3 high),裁决 opus high。

## 第 2 轮:修复 + 裁决(裁决 opus high,裁决模型 claude-opus-5-5;实现与修复模型 claude-sonnet-5-5)

### U0 本机安装与 detect 试点

修复:4 个子代理文件已放回 `~/.claude/agents/`(与移出的原件逐字节相同);引擎完整性人核——官方 engine-v0.1.14 的 `impeccable-darwin-arm64.sha256` 与本机 `~/.claude/skills/impeccable/scripts/bin/darwin-arm64/impeccable` 的 sha256 都是 `abbd69d540532b91e9599c41d3a6127dfbaabae5e24bafd74ff7e2fb18f4f87c`;艺术作品集站 4 个未复核子页做了渲染扫描(preview 服务起在 127.0.0.1:4391,扫完 kill 两个 PID,ps / lsof 核对退出):hero-eyebrow-chip 4 条(每页 1 条,套路类、有意版式)、low-contrast 2 条(roaming 页图号标签 #9a978f 在 #f3f2ef 上 2.6:1;tang-yunyu 页脚注上标 #d8401f 在 #f3f2ef 上 4.0:1)、em-dash-overuse 1 条(advisory)。静态 HTML 的 28 条 low-contrast 最终对账:25 条是背景推断错误,3 条渲染后仍成立(curating 页图注、roaming 页图号标签、tang-yunyu 页脚注上标),都是次要文字,是否有意弱化由主对话判断;渲染扫描同一规则在同一页只报第一个元素。没有 Chrome 时:把 IMPECCABLE_BROWSER / CHROME_PATH / PUPPETEER_EXECUTABLE_PATH 任一指到不存在的路径,detect 退出码 1、stdout 为 `[]`、stderr 写 Browser was not found——落在「detect 未跑」的判法里;自动查找失败那一路没有实测。

裁决:通过。第 1 轮 4 条 P1 全部闭合(裁决员自己复跑了哈希、cmp 子代理文件、无 Chrome 扫描、settings.json 与 ~/.claude.json 差异、进程与仓库只读)。新 P2 三条都是记录准确性:链里哈希缩写尾段写错(本节已改写全)、修复者返回里「共 5 条」实为 6 条、「另 26 条」应拆成 25 + 3(本节已按裁决员对账改正)、spec 第五节第 1 条的「待核」应改「已核」(已改)。

### U1 本机规则

修复:直通流程第 2 步的 detect 闸门括注与截图交付规范的 detect 句按 B 定稿整段改写;「只走下面的」改「只走本步的」;避开清单改成以 detect 套路类规则为基线、逐轮补;备份 `~/.claude/CLAUDE.md.bak-20261011-impeccable-rea-r2`。

裁决:通过。跨单元 P1 与 6 条 P2 全部闭合。新 P2 两条记遗留:单元没有可起的本地页面、只跑了源码扫描时,规则没要求在评审 prompt 里写明「渲染扫描未跑」(spec B.1 自身如此);「hallmark 保留、双触发再去掉」没写进本机规则(公开仓与内部工具包都写了)。

### U2 公开仓

修复(c95b212,squash 到 b1ed4a6):四个文件补艺术站 `detector.ignoreRules` 豁免清单;README 中英 detect 闸门段按 B 定稿改写、门禁段写完整命令;避开清单基线化;补 A.4(不装 hook、不开 live、critique 不进评审链)、/impeccable critique 入口、hallmark 保留句;rea 段移到第八节末尾;模板补「拿不准按展示型处理」、`npx impeccable@<锁定版本>` 前缀与压缩句;`claude plugin validate --strict` 两个插件通过。

裁决:通过。P1 与 8 条 P2 全部闭合。新 P2 三条:门禁段「按上面的硬闸门判法」方向词指错、两份模板漏 low-contrast 由主对话判断的例外(这两条已在收尾由主对话改掉,264b893)、公开面只写 `<锁定版本>` 占位而 rea 段写了 6.4.0(保持:公开面不钉本机版本,rea 的版本号是示例命令的一部分)。

### U3 内部工具包

修复(fd5b2e8,squash 到 275a6ec):核心 skill 的 `[^orch]` 脚注与「取证前置(硬规则)」段按 main 逐字恢复;两处入口合成一个「细则与前端单元评审链前的 detect 闸门见 references/review-chain.md」,等量压缩只丢数字与重复字(wf-result 行的「~18k」、「(1–256)」、「;细则在 research.md」、「省略继承会话档位」、「(模型见二)」),核心字数 6499.29 → 6499.29(上限 6499.57,余量 0.28),四个禁令词 4/8/6/15 与 references/ 13 次与 main 相同;WORKFLOW.md、review-chain.md、main-gate.md、模板按 B 定稿改写;upstream-map 改成与实际 diff 一致;补 hallmark 保留句;去掉「。 →」;内部模板补 init、拿不准、门禁 detect 句。

裁决:通过。2 条 P1、6 条 P2、跨单元定稿全部闭合(裁决员逐段比对了六个保护段、重算了字数与禁令词次数、重跑了 --strict 校验)。新 P2 三条:核心第 50 行删「省略继承会话档位」后括注「(非 API 默认)」语义残缺、第 52 行少一个空格(都因字数上限留着,信息在二节开头还有,记遗留);模板门禁句漏 low-contrast 例外(已在收尾改掉,fd379fe);Progress 把 review-chain.md 的改动写成「一句」(已改)。

### 结论与遗留

四个单元全部通过,P0/P1 无未闭合。遗留 P2:本机规则缺「渲染扫描未跑」的记法与 hallmark 保留句;核心 skill 第 50、52 行的括注与空格;text-overflow、text-occlusion、script-error、content-hidden-at-rest 四条硬闸门规则试点未触发、待有真阳性样本补测;本机 node 22.17.1 低于 impeccable 包要求的 22.18.0(能用,有警告)。
