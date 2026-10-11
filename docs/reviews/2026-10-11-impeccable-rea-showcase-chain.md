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
1. P1(镜头 A、B 同报)spec 第二节第 2 步与验收条款 3 写的「下载到 ~/.impeccable/bin/、launcher 校验 sha256」在本机不成立:引擎随安装器放在 skill 目录 `scripts/bin/darwin-arm64/`,launcher 对已在缓存或同级的引擎不校验。两位评审各自对照官方 engine-v0.1.14 的校验文件核过本机引擎哈希一致(abbd69d5…f87c2ec)。处理:spec 已改写,第 2 轮 U0 复核并把数值记进本文件。
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
