#!/bin/sh
# speak-human 常驻注入(plugin 版):标志文件存在才注入,否则静默退出。
# touch ~/.claude/.speak-human-always 开启;删除该文件关闭(关后仍可 /speak-human 手动触发)。
FLAG="${HOME}/.claude/.speak-human-always"
[ -f "$FLAG" ] || exit 0

SKILL="${CLAUDE_PLUGIN_ROOT}/skills/speak-human/SKILL.md"
[ -f "$SKILL" ] || exit 0

# 剥掉 YAML frontmatter(首个 --- 到第二个 --- 之间),只注入正文
awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$SKILL"
