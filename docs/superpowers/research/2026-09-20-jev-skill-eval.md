# 调研:jev-skill 要不要装、要不要融合进 workflow kit(2026-09-20)

> 状态:定稿。三票 `opus` 评审(结论与适配 / 数据去向与依赖 / 边界与异常情况)均判"结论成立,需修改",修改意见已由主对话逐条到源头核实后并入。星数、价格均为 2026-09-20 读数。

## 需求

Tony 原话:"如果我想给workflow里面加 jev-skill 这个东西的话,你看看有没有安装的必要,有没有融合的必要"。

## 结论

**现在不装进 kit,也不融合;kit 不需要做任何改动。** 无论你指的是哪一个同名仓库,这个结论都成立。四条理由,按分量排序:

1. **kit 里没有适合它的位置。** Jev 只回答选择题、打分题、是非题,输入上限约 32k token,不给理由。kit 里的判断分三类:
   - 脚本按固定规则判的(拦提交、清 worktree、`send-to` 找目标会话):必须每次结果一样,规则里明写"不许放宽成模糊匹配",不能换成"大概率对"的模型。
   - Claude 边读代码边判的(合并前要不要问你、任务怎么拆、下一步做什么):判断依据是代码、改动、整段对话,这些 Jev 拿不到,也放不进 32k。
   - 需要独立评委的(评审、speak-human 自检):这里第二个模型是有价值的,但要的是"哪一句有问题、违反哪一条"这种能照着改的具体意见,Jev 只回分数。
2. **数据会出内网。** kit 的规则同时发给 stellark 和 huake 两处内部镜像,huake 那条本地模型通道存在的理由就是数据不出内网。读过的每个 Jev 集成都要把中文消息、分支名、提交标题、改动内容或整段对话发到美国的主机;厂商隐私政策写的保留期是"合理必要的时间",没有具体期限。kit 的 hook 现在不联网、不要密钥、出错静默放行(`grep -rnE 'curl|wget|https?://' plugins/*/hooks/*.sh` 无结果;超时 5 秒 / 15 秒),接入后这三条都保不住。
3. **没有证据说明加了会更好,开销确实会上升。** 唯一一份"agent 加 Jev 前后对比"的试验(`wuyoscar/jev-skill` 作者自测,12 对,跑的是 DeepSeek 不是 Claude):不加 12/12 完成,加了 10/12,差的 2 次全在 4 个任务中的 1 个上,其中 1 次是东西做出来了但没在步数内声明完成;调用次数 100→133,花费 $0.0051→$0.0091,单回合耗时 6.3 秒→12.6 秒。样本太小,只能说"没看到变好"。中文方面只有一份小样本(`judgekit`,130 条,作者自己标注,仓库 1 星):Jev 97.7%,关键词规则 91.5%——对 Jev 有利,但同一张表里通用小模型 GLM-5.3-flash 也是 97.7%,说明即便将来需要语义分类,Jev 也不是唯一做法。
4. **厂商还在抢先体验阶段,周边全是一周内的新仓库。** 官方发布博客写明 Jev 处于 early access、按排队名单放号;OpenRouter 把对应接口归在 alpha 分组。GitHub 搜 `jev-skill in:name` 共 43 个结果,其中 40 个建于 9 月 16~20 日(另 3 个是名字碰巧相似的无关老仓库),名字一字不差叫 `jev-skill` 的有 9 个。

**不建议装 `codaaiteam/jev-skill`。** 该仓库与 `jevtypesafeai.com` 是同一作者(`plugin.json` 的 author.url 指向该站),默认把请求内容和 `jv_live_` 密钥发往该站的 `/api/v1/decide`。仓库 README、SKILL.md 和网站页脚都自述与 TypeSafe AI 无关,是架在官方接口前面的计费转发服务,卖点是"不用排队";定价页 $0.25~0.42/百万输入 token,约为官方标价 $0.042 的 6~10 倍(官方通道目前要排队)。仓库无许可证,2 次提交,0 星。它没有隐瞒什么,问题在于请求内容和密钥要交给一个无法验证其处理方式的第三方,而官方直连的路是存在的。

**如果只是想自己试试 Jev**,用官方的 `typesafe-ai/skills`(MIT,约 1150 星,2026-08-24 建,仓库里只有说明文档和插件清单,没有可执行代码)。四个条件:

- 只装在你个人机器上,不进 kit 的 `plugins/`,不进 stellark、huake、公开 GitHub、Codex 任何一处镜像。
- 安装时不联网、不要密钥;**但每次用它,Claude 都会按它的指示去读 docs.typesafe.ai 的在线文档**,远端内容随时可改,改了不会经过你的任何检查。它教你写的程序仍然需要 TypeSafe 密钥(目前要排队)。
- 固定版本:它的 `plugin.json` 写的是 0.5.7,第三方插件市场默认不自动更新,本地副本不会自己变;想更稳就手动复制某个提交的 `SKILL.md`。
- 公司或客户的文字不要作为输入发给 Jev。

它的用途是"教 Claude 帮你写调用 Jev 的程序"。你手上暂时没有这类产品功能,所以这一步也可以不做。

**装了怎么卸:** 官方 skill → `claude plugin uninstall typesafe@typesafe-ai`,再 `claude plugin marketplace remove typesafe-ai`(手动复制的就删掉 `~/.claude/skills/` 下对应目录),顺带看一眼 `~/.claude/plugins/cache`。如果试过下文那几个"挑 skill"的工具:删掉它们写进 `~/.claude/settings.json` 的 hook 条目和 `skillOverrides` 内容(`jev-skill-gate` 从不写 `off`,残留会让 skill 一直停在"只留名字"),删缓存(`~/.cache/skillful/routes.json` 等),删 `~/.config/jev/credentials`,并到服务商后台作废密钥。

## 内部检索(github-research 第 0 步)

读了本地 `/Users/tbata/Tony/Proj/Stellark/Projects/code-base/components.yaml`(1537 行)。没有"只回答选择/打分/是非题的判断模型"这类组件。相近的三个都是产品级的,kit 自己用不上:

| 组件 | 能力 | 与本题的关系 |
|---|---|---|
| `ai-category-oem-classifier` | 规则优先、模型补充、置信阈值、人工复核队列的分类流水线 | 将来某个产品要做大批量分类时,它是与 Jev 同台比较的内部候选 |
| `stella-llm-client` | OpenAI 兼容的模型调用客户端(Go) | 同上,调用层 |
| `huake-llm-client-dual-provider` | 本地 Ollama / 云端 DeepSeek 双通道客户端 | 同上;数据不出内网的选项 |

本次未采用内部组件,`used_by` 无需登记。

## Jev 是什么

| 事实 | 来源 | 性质 |
|---|---|---|
| TypeSafe AI 出的托管计费模型,2026-09-17 前后发布;只返回选择(Choice)、打分(Score)、是非概率(Noul),不生成文字,不给理由 | typesafe.ai 发布博客 | 厂商说法 |
| 发布时处于 early access,按排队名单放号;单一厂商,没有可自行部署的版本 | 同上(评审到源头核实原文) | 已核实 |
| 官网 typesafe.ai,文档 docs.typesafe.ai,官方接口 `https://api.typesafe.ai/v1/systemone`;文档站与博客都链接到 GitHub 组织 `typesafe-ai` | 主对话 `curl` 两个页面核实 | 已核实 |
| 官方 skill `typesafe-ai/skills`:MIT,约 1150 星,仓库共 6 个文件(2 个清单、2 个 LICENSE、README、SKILL.md),2 次提交;SKILL.md 指示 agent 使用时去读 docs.typesafe.ai 的在线文档 | 主对话与两票评审分别用 GitHub 接口核实 | 已核实 |
| 价格 $0.042/百万输入 token,输出免费;单次判断约 $0.0004;耗时 70~500 毫秒 | 厂商博客;OpenRouter 模型页标价相同 | 厂商说法 |
| 输入上限约 32k token | OpenRouter 模型页写 32K;`jev-review` 与 `fast-jev-compaction` 的 README 各自实测到同一上限;厂商文档未写 | 多方印证 |
| 隐私政策:不拿客户输入训练;保留"合理必要的时间"(无具体期限);服务在美国;输入可提供给其服务商;含并购转让条款 | typesafe.ai/legal/privacy-policy | 厂商说法 |
| "不会幻觉"指输出格式不会错,不是答案不会错 | 厂商博客 + 第三方评论 | 已交叉印证 |
| 经 OpenRouter 调用走 `/api/alpha/decisions`,官方文档把它归在 alpha 分组,只有一个提供方;该模型不在 OpenRouter 公开模型列表(`/api/v1/models`)里 | 评审核实文档导航、模型页与模型列表 | 已核实;能否稳定使用未验证(不允许发请求) |

## "jev-skill"指哪个

| 仓库 | 星 / 许可证 / 建仓日 | 是什么 | 数据发给谁 / 用哪把密钥 | 判定 |
|---|---|---|---|---|
| `typesafe-ai/skills`(官方) | 约 1150 / MIT / 08-24 | 说明文档型 skill,教 agent 写调用 Jev 的程序 | 自身不发请求;使用时读 docs.typesafe.ai | 想试就用它,条件见上 |
| `tamaratran/fast-jev-compaction` | 5201 / MIT / 09-17 | Claude Code 插件:上下文快满时,用 Jev 给每条工具调用打分,删掉过时的,代替自带的压缩摘要 | `api.typesafe.ai`;`TYPESAFE_API_KEY`;**每次压缩发送整段对话** | 这批里唯一真有人用的 Claude Code 集成,也最贴近你长会话的用法;见下 |
| `wuyoscar/jev-skill` | 152 / MIT / 09-20 | 9 个 skill 文件夹 + 案例合集 + 中文 README;不装 hook | OpenRouter;`OPENROUTER_API_KEY`(只读环境变量) | 第三方里最认真,如实公布了负面结果;一天内写完,无使用历史 |
| `dbreunig/building-with-jev-skill` | 126 / 无 / 09-17 | 纯文档:怎么设计 Jev 问题 | 不发请求 | 无许可证,不能转载进 kit |
| `NiazMorshed2007/jev-review` | 184 / MIT / 09-17 | 本地 MCP 服务,把任务、改动、文件、仓库信息发给 Jev 按 15 个维度打分 | `api.typesafe.ai`;`JEV_API_KEY` | 只给分数不给理由,与 kit"评审只报具体发现"的要求不合 |
| `Barba-Tech-CO/jev-claude-skill` | 0 / MIT / 09-19 | 约 400 行纯标准库 Python 客户端 | 官方 / Vercel / OpenRouter 三选一;密钥存 `~/.config/jev/credentials`(0600) | 代码干净,单人一天产物 |
| `AndyTheFactory/jev-skill` | 0 / 声明 MIT 但缺 LICENSE 文件 / 09-20 | Python 包 + skill;默认只记录、不影响 agent | OpenRouter;`OPENROUTER_API_KEY` | 设计谨慎,三小时内写完,无使用历史 |
| `codaaiteam/jev-skill` | 0 / 无 / 09-19 | 4 个文件 | `jevtypesafeai.com`(第三方计费转发);`jv_live_` 密钥 | 不建议装,理由见结论 |

**`fast-jev-compaction` 为什么现在也不装:** 它要把整段对话(含所有工具输入输出,也就含公司代码和数据)在每次压缩时发到美国的接口;依赖 Claude Code 尚在抢先体验的"函数 hook"功能(要设 `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`,2.1.274 起);密钥要排队;建仓 4 天已有 58 个未关闭问题。它的库在 Jev 出错、缺密钥、内容放不下时会抛异常,Claude Code 里的 hook 会退回自带摘要。它与 kit 无关,属于你个人用不用的问题;过了下面的复查条件再看。

## kit 里哪里可能用得上

| 判断点 | 现在谁判 | Jev 合适吗 | 原因 |
|---|---|---|---|
| 拦提交的 hook(识别一条命令是不是真的 `git commit`) | 脚本,按命令写法的固定规则 | 不合适 | 要的是每次结果一样、可逐行检查 |
| 清 worktree 的 hook(能不能删) | 脚本,五个条件全满足才删 | 不合适 | 删错不可恢复;输入是 git 状态,不是自然语言 |
| `send-to` 找目标会话 | 脚本式规则:精确→前缀→子串 | 不合适 | 规则明写"不许自行放宽成模糊/编辑距离匹配",多个命中必须问你 |
| 并 main 前要不要问你 | 主对话 Claude | 不合适 | 要读懂改动对页面的影响;改动放不进 32k;规则已写"拿不准就问" |
| 派哪档模型与思考深度 | 主对话 Claude | 不合适 | 这是模糊判断(常规实现还是难点实现),形式上对口;但判错的代价已被"失败才升档"吸收(重跑一轮),换来的是每次派工多一次外网调用和一把密钥 |
| 任务能不能并行拆、文件会不会撞 | 主对话 Claude | 不合适 | 要读懂代码 |
| `whats-next` 判断下一步、`sop-generate` | 主对话 Claude 读项目文档 | 不合适 | 依据是整份文档与进度,不是一段短文字 |
| 评审过不过 | `opus` 子代理 | 不合适 | 评审要给出具体问题,Jev 只给分数;一个单元的改动加 spec 放不进 32k(第三方客户端上限更低:8,000 / 60,000 字符) |
| speak-human 运行时自检(每次开口前自查) | 同一个 Claude 查自己刚写的话 | 不合适 | 独立评委在这里有价值,但要的是"哪句话违反哪一条";Jev 只回分数;每次输出前多一次外网往返 |
| `DECISIONS.inbox.md` 消化(每条归为决策 / 需求 / 噪音) | 主对话 Claude,提交前顺手判 | 弱 | 全 kit 唯一的"短文字三选一",形式最对口;但把需求错判成噪音等于需求消失,而 Jev 不给理由、没法复核;一次只有几条,不是批量 |
| 自动铺脚手架的离线评测(15 条,模型只回 `TRIGGER` / `NO_TRIGGER`) | 脚本调 `claude -p` | 弱 | 形式上就是二选一;但评测的目的是检验线上做判断的那个 Claude 读规则文本读得对不对,换评委就不再检验线上行为;验收线要求"唯一允许的错必须是漏判",Jev 判不了;一年跑几次 |
| speak-human 的离线评测(按评分标准打分) | 脚本调 `claude -p` | 弱 | 要逐条给出违反了哪条及理由;换评委会让新旧分数不可比 |
| `ui-sweep` 假阳性定性(每轮上百条 `dead` / `click-error` 归因) | 主对话 Claude 对着记录和截图判 | 弱 | 全 kit 唯一"一次几百条"的批量分类,是 Jev 被验证过的用法;但要看截图与页面语义,一年跑几次,且规则要求真缺陷必须用真浏览器逐条复核 |
| 需求/决策信号提醒 hook(每条用户消息过一遍词表) | 脚本,词表匹配 | 弱 | 见下 |

**信号提醒 hook 单独说明。** 这是 kit 里唯一"本来就允许判错"的地方:2026-08-14 五轮修改后,词表法在"与软件无关的生活句子"上误报到了上限,你当时定的是"高召回软提醒,领域内误报可忽略"。`judgekit` 的数据(中文工单/紧急度分类,Jev 97.7% 对关键词规则 91.5%)说明理解语义的模型在相近任务上确实比词表准。但要付出:每条用户消息都发往美国的主机;hook 要在 5 秒内完成一次跨境往返,网络不通或密钥失效时必须静默放行并退回词表,否则每轮对话都会被拖住;kit 分发到本机、stellark、huake、公开 GitHub、Codex 五处,付费且要排队的密钥不能是必需项,只能做成可选;再加中英双语与各处镜像的维护。换来的只是一条软提醒少几次误报。不值。

## 证据:加了 Jev 会不会更好

| 证据 | 结果 | 谁测的 |
|---|---|---|
| `wuyoscar/jev-skill` 的 agent 对照试验(4 个任务 × 3 次 × 2 组 = 12 对,DeepSeek V4.1 Flash) | 不加 12/12,加了 10/12;0 胜 10 平 2 负;差距全在"目标恢复"一个任务上(3/3→1/3),其中 1 次是产物做出来了但没在步数内声明完成;工具报错 9→13;调用 100→133;花费 $0.0051→$0.0091;单回合耗时 6.33 秒→12.57 秒 | 仓库作者;主对话与两票评审分别读原文件核实。作者自注"小规模试验,不代表一般结论";跑的不是 Claude |
| 同仓库的校准测试(BBH 160 题) | Jev 总体 136/160 = 85%,同题 DeepSeek 严格接口 120/160 = 75%;分任务 55%~100%,总体数字信息量有限。两个不同的切片:自称把握 ≥0.90 的 100 题里错了 8 题;概率最高一档(118 题)平均自称 98.1%,实际对 89.0% | 同上 |
| `judgekit` 中文小样本(130 条:工单派单、情感、垃圾评论、紧急度) | Jev 97.7%(127/130,95% 区间 93.4~99.2,三次运行结果一致,约 890 毫秒);GLM-5.3-flash 97.7%;deepseek-flash 96.2%;关键词规则 91.5%;本地 0.6B 小模型 61.5% | 仓库作者自标注,1 星;其模型对照组完整运行仍标"待做"。主对话读 README 核实数字 |
| 厂商自己的四项流程基准(第三方评论 Anthony Maio 转述并批评其方法) | Jev 67.8%,Claude Sonnet 5 67.8%,GPT Terra 67.9%,Claude Opus 5 73.1%,GPT Sol 74.1%;发票处理 Jev 61.8% 对 Sol 79.1%;参考答案是两个模型高推理输出的平均,不是真实标注 | 厂商自测;主对话读评论原文核实。Jev 与 Sonnet 5 持平而便宜得多,这对"大批量分类"有意义,对 kit 没有,因为 kit 没有大批量分类点 |
| awesome-jev 收录的第三方评测 | 3.3 万条目录的重排没有胜过向量检索;Amazon 商品相关性 6 项里 4 项不达标;本地小模型 Luce 在 3 项分类上都高于 Jev | 各评测作者;子代理读清单转述,未逐个打开原仓库 |

## "用 Jev 挑 skill"这一类

与你的现状相关:你装了一百多个 skill,其中个人目录 `~/.claude/skills` 下 26 个,其余来自插件。

| 仓库 | 怎么接进 Claude Code | 每次发出去什么 | 作者自己的证据 | 判定 |
|---|---|---|---|---|
| `ShivamPansuriya/jev-skill-gate`(2 星,MIT,09-17) | 装一个会话开始时运行的 hook,自动改 `~/.claude/settings.json` 里的 `skillOverrides`,把低分 skill 设成"只留名字"或"只能手动调用" | 每个会话一次(缓存 7 天):skill 名称与描述、技术栈、目录结构、分支名、最近提交标题、依赖名、README 摘录 | 20 例里只有 4 例真的调了 Jev,其余用的是本地关键词打分;全英文 | 它宣称的"清单缩短 75%"对你大部分不适用:`skillOverrides` 管不到插件带来的 skill;还会自动改你的全局设置 |
| `bestagentkits/jev-skillful`(1 星,MIT,09-17) | 装一个每条用户消息都运行的 hook,先在本地筛出约 15 个候选,再问 Jev,把"建议用哪个 skill"加进上下文 | 每条消息:消息原文 + 候选 skill 的名称与描述(可关掉原文上传) | 自测召回 0.60,没达到自己定的 0.90;越南语消息只有 0.429,原因是 skill 描述是英文;"加了提示后任务是否做得更好"的测试建了但没跑 | 只能加提示,不能缩短清单;每条消息多等最多 2 秒 |
| `win4r/jev-skill-suggester`(27 星,MIT,09-19) | 不是 hook,是给 Codex 用的 skill + 命令行工具,只在被点名时运行 | 被调用时:任务描述 + 候选 skill 的名称、描述、节选 | 16 例(含几例中文)0 例推荐错;单人当天测;整个仓库只有 1 次提交 | 面向 Codex 的目录,不会自动接进 Claude Code |
| `GodsBoy/jev-agent-skill-router`(11 星,MIT,09-16) | 不适用:面向 Hermes(另一个 agent 程序),数据是人工编的英文样本 | — | — | 与 Claude Code 无关 |
| `kerpopule/hermes-jev-skills`(约 265 星,MIT,09-18) | 绝大部分功能只对 Hermes 有效;对 Claude Code 只是几个普通 skill 文件 + 一条要手动调用的命令 | 被调用时才发;非拉丁文字的消息一律发往网络 | 没有按语言分开的准确率 | 这批里提交最多(49 次),但不是给 Claude Code 做的 |

**要点:**

1. hook 只能往上下文里加内容,不能删掉已加载的 skill 清单(两个仓库的作者都明说了)。"每条消息问一次 Jev"省不了 token,只会多一段提示、多一次等待。
2. 想精简 skill 清单不需要 Jev,Claude Code 自带两个入口(官方文档 code.claude.com/docs/en/skills):
   - 个人和项目目录下的 skill:`/skills` 菜单,选中按空格切换状态,按 Esc 保存到当前项目的 `.claude/settings.local.json`。四种状态:`on`、`name-only`(只留名字)、`user-invocable-only`(对模型隐藏,仍可手动调用)、`off`。
   - **插件带来的 skill 不受 `skillOverrides` 影响,要到 `/plugin` 里管。**
   - 优先用 `name-only`,少用 `off`:自 2.1.199 起 `off` 还会让这个 skill 从远程控制客户端和 Agent SDK 的命令列表里消失,按全名调用会报错,而你经常通过 HAPI 远程操作会话。
   - 全局规则点名要用的 skill(`stellark-workflow`、`speak-human`、`github-research`、`send-to` 等)不要关;关了不会有任何警告,规则会悄悄失效。
3. 你并没有反映过"Claude 选错 skill"这个问题。

## 什么时候值得再看

每条都能用一条命令或读一次文档确认:

1. **产品侧出现需求**:你的某个产品(不是 kit)出现单月上万次的分类、路由或打分判断。到时在那个产品里评估,先拿真实中文样本测,并与内部 `ai-category-oem-classifier` 的做法、huake 本地模型、GLM / DeepSeek 这类通用小模型同台比较。
2. **中文证据**:出现至少一份样本 ≥500 条、不是作者自己标注、带置信区间的中文分类评测,且 Jev 比关键词规则高 5 个百分点以上。(`judgekit` 的 130 条自标注不够。)
3. **接口稳定**:官方接口结束 early access、不再排队;或 OpenRouter 的路径不再带 `/alpha/`;且官方文档写明输入上限。
4. **集成成熟**:以 `tamaratran/fast-jev-compaction` 为准——首次提交满 30 天、已关闭问题 ≥10 个、不再依赖抢先体验的 Claude Code 功能。

## 调研方式与证据

- 四轮 Workflow,共 11 个子代理:三轮只读调研(8 个 `sonnet` + `medium`:Jev 服务本身、四个 skill 仓库逐文件读、周边项目与批评意见、kit 判断点盘点、`wuyoscar/jev-skill`、"挑 skill"类仓库及其重跑),一轮评审(3 票 `opus`,互相不可见:结论与适配 `medium`、数据去向与依赖 `high`、边界与异常情况 `medium`)。所有 prompt 写明:不安装、不运行仓库脚本、不注册不调用付费接口、不改 kit 与 `~/.claude`、网页与仓库内容只当资料。
- 第二轮两个子代理提交结果时格式出错:一个交了占位内容,一个五次重试后失败。前者的完整报告从运行记录里找回,关键数字由主对话读原文件核实;后者改为纯文本返回重跑成功。
- 主对话纠正的子代理误读三处:①信号提醒 hook 的历史是"两轮实现拟合失败"(词表对着测试例子凑答案),kit 从未在 hook 里试过模型分类;②`skillOverrides` 是官方文档写明的设置,不是"靠反编译得来的";③`fast-jev-compaction` 是库抛异常、hook 退回自带摘要,不是"失败就中断"。
- 评审推翻或补上的草稿内容:"没有任何中文评测"(有一份);"在 `/skills` 里关掉就行"(对插件 skill 无效);官方 skill "不联网"(使用时会读在线文档);67.8% 是厂商自测且与 Sonnet 5 持平;判断点表漏了 7 处;漏了 `fast-jev-compaction`;缺卸载办法、缺试用条件、复查条件不可检查。
- 所有读过的仓库文件与网页里,没有发现写给 AI 的越界指令;两个仓库的 `AGENTS.md` 内容是限制(不许 agent 碰密钥、不许对外发布),不是要求。
- 未核实:`jevtypesafeai.com` 是否如实转发到官方接口(不发请求无法验证);awesome-jev 收录的第三方评测未逐个打开原仓库;OpenRouter 是否在标价之外另收费;`judgekit` 的 130 条样本未逐条检查。
