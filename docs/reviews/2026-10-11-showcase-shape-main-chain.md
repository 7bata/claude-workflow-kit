# 评审链:展示型前端的方向在主对话定、子代理只做建造

spec:`docs/superpowers/specs/2026-10-11-showcase-shape-in-main-conversation-design.md`。单元:U1 本机全局规则、U2 公开仓(README 中英、两份模板、插件 0.19.1)、U3 内部工具包(该仓分支 `wip/showcase-shape-main-2026-10-11`,细节记在该仓)。实现全部 sonnet medium(实现模型 claude-sonnet-5-5;U2 提交 1d30ce6,U3 提交 f290cb0,U1 不在 git 里、备份 `~/.claude/CLAUDE.md.bak-20261011-shape-main`);盲审 opus medium,裁决 opus high。

## 第 1 轮:盲审(每单元 2 个,镜头 A 正确性 / 镜头 B 边界与各面一致)

### 跨单元(三面都有)

1. **P1(U1 两个镜头同报,U2 镜头 A、B 同报,U3 镜头 A 在「复核点」里把删掉这句记成了正确)**:原规则「该项目第一次用时由主对话先跑一次 `/impeccable init`」是无条件的;这次把 init 挂到了第 0 步「新页面或换视觉风格」那段下面,而同段写明局部扩展与打磨「不走这段」。没有 PRODUCT.md 的项目若第一件展示型活是打磨或局部扩展,规则里就没人跑 init。主对话核实:impeccable SKILL.md 第 77 行的路由写明「窄范围修改在没有 PRODUCT.md 时照旧进行、事后建议 init,不阻塞」,所以 polish 不会卡住;但规则丢了原有的无条件句,仍按 P1 修——第 0 步写成「没有 PRODUCT.md 时,不论本次是哪一种,主对话都先跑一次 init」。
2. **P1(U1 镜头 B)**:comp-led 路径还有一个要人批准的环节没分配——visualize.md「One approval point」要求把三张构图样稿交使用者批准一张,「no substitute and no skip condition」「never delegated」,发生在 new-work 第 5 节末尾、第 6 节建造之前;批准的样稿路径记在 surface brief、sidecar 写 `approved: true`,`.impeccable/mocks/decision/` 下的样稿「imply no approval on their own」。主对话核实原文属实(visualize.md 第 25~33 行)。修法:第 0 步写明这一轮也由主对话做、不许替使用者选;「批准的样稿落在 decision/」改成「路径以 surface brief 记的为准」。
3. **P2(U1 镜头 B)**:shape 自己「stop before persistence」(shape.md 第 39 行、new-work.md 第 93 行),不写 direction contract;措辞要写明 shape 之后由主对话接着走 new-work 第 1~5 节把记录写完。主对话核实属实。
4. **P2(U1 镜头 A、U2 镜头 A)**:spec 里没有方向、direction contract、样稿路径时子代理怎么办没写;合理预期是停下报缺,不自己跑 shape、不编方向。
5. **P2(U1 镜头 B,U3 镜头 B 在模板上同报)**:「init、shape 与方向选定不派给子代理」一概而论,而局部扩展走 new-work「扩展既有页面」路径时 impeccable 自己要「shape those directly」并做一次简短确认——要写明不派的只是新页面或换风格的那次 shape,局部扩展的简短确认与直接 shape 由子代理按 spec 与 DESIGN.md 做。
6. **P2(U2 镜头 A、B 同报)**:七.1 新段加了 spec 没有的限定「impeccable 已装的机器」,没装 impeccable 只用 hallmark / frontend-design 的机器上,新页面方向由谁定没写(公开仓读者多半没装)。修法:没装的机器同样由主对话用备用 skill 把方向定下写进 spec。
7. **P2(U1 镜头 A)**:critique 列在子代理 stage prompt 第一步要做的事里又叫「手动入口」,读起来像子代理也能跑;「不进评审链」同段说了两次。修法:审查已有页面归主对话手动 `/impeccable critique`,只保留一处「不进评审链」。

### U1 本机全局规则

除上面 1、2、3、4、5、7 外无其他发现。复核点:diff 只改三处(角色表第 11 行、第 0 步第 53 行、第 2 步第 55 行);备份存在;验收条款 1 关键词全在;旧说法「先调设计 skill」「拿到方向后再动手」「整体改版走 shape」已删;避开清单、管理后台不调、不装 hook / 不开 live 原样;实现者把「之后再点名」改成「派工时再点名」语义不变。

### U2 公开仓

除上面 1、4、6 外:
- **P1(镜头 B)**:两份模板 §7 第 96 行压缩句写成「主对话……选定方向卡」(英文 "picks the direction card"),只装插件的人照它做会由主对话自己挑卡、不问人——「由使用者选」这个要素压没了。
- P2:七.4 末尾残留「拿到方向后再动手」(英文 "only after getting the direction does the agent start"),局部扩展与打磨没有可「拿到」的方向,会被读成 polish 也要等方向;七.4 里「已在 brainstorming 由主对话做完(见七.1)」与「方向按七.1 由主对话在 brainstorming 定」重复、后者是从原 init 句改来的;英文模板第 124 行语法不通(主语错位、悬垂分词);中文模板第 124 行派工句没写「第 6 节」「扩展路径」「按批准样稿建造」,实现者返回里却写了;验收条款 2 的字面短语按原文 grep 不到(括号里多了「,写进 spec」、全角标点),语义都在。
- 复核点:README 中英七.1 / 七.4 / 角色表要素齐、英文逐句同义;原有要素(hallmark 双触发、不装 hook、不开 live、critique 不进评审链、避开清单、管理后台不调、detect 闸门)都在;两个 plugin.json 0.19.1;公开文件 grep /Users/、stellark、gitlab、hapi、huake、dev-toolkit 无命中;spec 第四节四条情形覆盖情况逐条核过。

### U3 内部工具包

无 P1。P2:核心七.1 没有指向 references/frontend.md 的触发句、核心七.4 末句仍是「展示型先调设计 skill」(spec 限定核心只改第 18 行,属 spec 取舍,但与第 18 行新说法对不齐);模板第 128 行没限定「新页面或换风格」、没写「局部扩展与打磨直接派子代理」、保留了「先调设计 skill」旧说法;upstream-map 第 58 行旧记录没标被取代、本批记录漏了 frontend.md 第 1 行「何时读」的改动;frontend.md 派工节逐字镜像带来的「见七.1」「只走前面的」在只有插件的读者手里没有着落。复核点:frontend.md 派工节与新节分别与 WORKFLOW.md 七.4 / 七.1 逐字相同(Python 比对,986 字符);核心只改第 18 行,字数 5813.57 → 5829.14(≤ 6500);wip 分支远端 f290cb0 与本地一致;角色表行、parallel-do、模板第 100 / 128 行都改了;Progress 条目存在。

### 分流

U1、U2 有 P1 → 修复后裁决;U3 只有 P2,但跨单元修复(1、6 与模板限定句)要动它的文件,一并修复、一并裁决。核心 SKILL.md 现有余量(5829 / 6500),spec 放开核心七.1、七.4 末句两处短句,仍 ≤ 6500。修复各派一个 sonnet medium 实现 agent;裁决三个 opus high,各带本文件全部发现。

## 第 2 轮:修复 + 裁决(修复模型 claude-sonnet-5-5;裁决 opus high,裁决模型 claude-opus-5-5)

### U1 本机全局规则

修复:第 0 步 A 段、第 2 步 B 句、角色表 C 句按 spec 四之二整句替换;备份 `~/.claude/CLAUDE.md.bak-20261011-shape-main-r2`。裁决:通过,第 1 轮跨单元 1~7 与本单元各条全部闭合(裁决员 diff 两份备份、grep 关键词与旧说法、对照 impeccable 原文)。新 P2 三条:① 停下条件「spec 里没有这些路径」把批准样稿也算进去,code-led 或没有图像生成时本来就没有样稿,子代理会白停一轮——已在收尾由主对话改成「没有 surface brief 路径、或 brief 里没有 direction contract 才停,样稿只在 comp-led 时要求」(四面同改);② build-phase 状态交接没写(样稿轮在 `impeccable build-phase` 的 comps 阶段跑,子代理从第 6 节起会不会重跑 start、能不能接上 spec 阶段,或改用 `start --comp`)——记遗留,等第一次实跑核对;③ 三张构图样稿怎么摆到使用者面前(visualize 只认本地决策页或能显示图片的界面,HAPI 手机端看不到本机页面;「不许替使用者选」与 impeccable 允许使用者明说代选不完全一致)——记遗留,与 spec 第四节第 4 条同类,可按「截图交付规范」打包 HTML 发出、代选照 impeccable 记录在案。

### U2 公开仓

修复(bd1cfbf,squash 到 1d30ce6):README 中英七.1 A 段(去掉「impeccable 已装的机器」限定)、七.4 B 句(删重复句与「拿到方向后再动手」残句)、角色表 C 句;两份模板第 124 行派工句(英文语法改通)、第 96 行半句(方向卡与构图样稿由使用者选定、批准);validate --strict 通过。裁决:通过,P1 一条与 P2 各条闭合(验收条款 2 的字面短语 grep 不到仍是 P2:语义都在、字面不同)。新 P2 三条,已在收尾由主对话改掉:模板 §7 第 96 行把 init 挂在「新页面或换风格」下面、读起来像打磨不用 init(中英都改成「没有 PRODUCT.md 时先 init,不论哪种活;新页面或换风格再 shape」);七.4 critique 句没写由谁做(中英补「由主对话」);模板第 124 行「shape、方向卡与构图样稿都由使用者选定、批准」把 shape 也算成使用者选的(改成「主对话跑 shape,方向卡由使用者选定、构图样稿由使用者批准」),「让它避开」的「它」改成「让 impeccable 避开」。

### U3 内部工具包

修复(a8b4eb0,squash 到 f290cb0):WORKFLOW.md 三处、frontend.md 两节同步、核心七.1 触发句与七.4 末句(5829.14 → 5870.14)、模板第 100 / 128 行、upstream-map、Progress。裁决:通过,各条闭合(裁决员复算字数、Python 比对两处逐字相同、复跑 validate、核对远端 sha)。新 P2 三条,已在收尾由主对话改掉:七.4 与 frontend.md 派工节「已在第 0 步由主对话做完」(WORKFLOW.md 没有「第 0 步」)改成「已在 brainstorming(见七.1)由主对话做完」,两处仍逐字相同;frontend.md detect 节引用的「上一节规则 A 末尾说的『只走前面的 detect 闸门』」原文已不存在,改成「派工节里说的『只走本步的 detect 闸门』」,新节标题去掉「第 0 步」;模板第 100 行 init 位置同 U2;upstream-map 第 58、59 行旧记录加「已被本批取代」。细节记在该仓 `docs/reviews/2026-10-11-showcase-shape-main-chain.md`。

### 结论与遗留

三个单元全部通过,P0/P1 无未闭合。遗留 P2(等第一次展示型前端实跑再定,不开新轮):build-phase 状态交接(主对话做完样稿轮后子代理怎么接 build 状态机);构图样稿在 HAPI 手机端怎么给使用者看、使用者明说代选时怎么记;验收条款 2 的字面短语与模板实际措辞不同(语义都在)。收尾手改后主对话复核:WORKFLOW.md 七.4 与 frontend.md 派工节、七.1 新段与 frontend.md 新节仍逐字相同;核心字数 ≤ 6500;kit 两个插件 validate --strict 通过;公开面无本机路径与内部名。
