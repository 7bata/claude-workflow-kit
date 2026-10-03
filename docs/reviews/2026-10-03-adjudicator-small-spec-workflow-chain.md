# 评审链:裁决轮用主对话模型 + 小改动也写小 spec 直接开干 + 并行派活统一走 Workflow

spec:`docs/superpowers/specs/2026-10-03-adjudicator-model-small-spec-workflow-dispatch-design.md`。本文件由主对话维护,每轮结束后追加;下一轮评审 prompt 给本文件路径,轮次计数由本文件继承。

单元与分组(实现模型在首轮实现后补实际模型 ID):U1 本机全局规则(S 组,sonnet + medium);U2 本仓 README 中英(O 组,opus + medium);U3 本仓三个 workflow 插件的模板、whats-next、scaffold 与版本号(S 组,sonnet + medium);U4 dev-toolkit(O 组,opus + medium);U5 huake 两个工具包(S 组,sonnet + medium)。评审三组,每组 2 个互不可见的 opus + medium 盲审:公开面(U2 + U3)、本机与 dev-toolkit(U1 + U4)、huake(U5)。裁决轮按本批的新规则用主对话当前的模型(Fable)+ high。本批不属于规则 3 的高风险类别。

执行:2026-10-03 本机 10 核,开跑前 1 分钟负载 7.3(超过 70%,未超核数),实现与盲审都按并发 2 分批跑。
