#!/bin/sh
# auto-scaffold 常驻注入(plugin 版):默认注入,opt-out 标志存在才不注入。
# 与 speak-human 的 opt-in(标志存在才注入)方向相反——本规则目标用户是不会
# 主动去开开关的 vibe coding 用户,装插件即视为选择进入方法论;误触发防线
# 放在规则正文的保守判定上(宁漏勿错),不放在开关上。
# touch ~/.claude/.auto-scaffold-off 即全局关闭(删除该文件重新开启)。

# 评测隔离开关:evals 跑分的 claude -p 子进程带上此环境变量,hook 静默不注入——
# 否则常驻用户跑评测时"基线"臂也会从 hook 拿到规则,两臂对照失效(仿 speak-human)。
[ -n "${AUTO_SCAFFOLD_EVALS_HERMETIC:-}" ] && exit 0

# 已在 git 仓里的会话,规则正文判定条件 2 永远不满足,注入纯属上下文浪费;
# 副作用是会话中途 cd 出仓将拿不到规则,属可接受取舍。
git rev-parse --git-dir >/dev/null 2>&1 && exit 0

FLAG="${HOME}/.claude/.auto-scaffold-off"
[ -f "$FLAG" ] && exit 0

RULE="${CLAUDE_PLUGIN_ROOT}/hooks/auto-scaffold.md"
[ -f "$RULE" ] || exit 0

# 规则正文无 YAML frontmatter,直接原样输出,无需剥离。
cat "$RULE"
