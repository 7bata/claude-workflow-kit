#!/usr/bin/env python3
"""rm-guard-cases.py: table-driven cases for the recursive-rm target guard hook
(hooks/block-recursive-rm.py).

Each case spawns a subprocess (default: `sh run-guard.sh block-recursive-rm.py` from the hooks directory;
with --direct: `python3 block-recursive-rm.py`), feeds a PreToolUse JSON payload
{"tool_input": {"command": ...}, "cwd": ...} on stdin and checks exit code, the
`rule=` line of the reason, and the stdout JSON.

Commands appear only as strings fed to the hook: nothing here executes a delete.
Every run creates one temporary directory with two subdirectories, `home` (the
subprocess HOME) and `work` (default payload cwd); only that directory is removed
at the end.

Case fields: id, cmd, cwd ("work" default / "home" / "none" = no cwd key in the
payload / "relative" = a non-absolute cwd / an absolute path), expect (deny|allow),
rule (deny only), target (optional: substring that must appear in the reason).
Placeholders in cmd and cwd: {HOME} (subprocess HOME), {REALHOME} (home recorded
by pwd), {REALHOME_PARENT}, {REALHOME_DSLASH} (parent + "//" + name), {WORK}, {BASE}
(the per-run temporary directory). `${HOME}` is not a placeholder.
Revision 2 additions (name = last component of {REALHOME}): {RN} (name), {RN2} / {RN3}
(first 2 / 3 characters), {RN_Q} (last character -> ?), {RN_BR} (second character in
[ ]), {RN_LASTBR} (last character in [ ]), {RN_PSTAR} (all but the last character + *),
{RN_MID2} (first two + * + last two), {RN_SEQ} / {RN_SEQ2} (last character as a brace
sequence), {RL0} / {RL0B} (first path level of the real home as a glob),
{BOOTLINK} / {HOMELINK} / {USRLINK} / {USERSLINK} (symlinks created in {BASE} that
point at /, the real home, /usr and the parent of the real home), {BOOTVOL_REAL} /
{BOOTVOL_REAL_ESC} (a symlink under /Volumes that resolves to /, probed at run time;
cases that need it are skipped when the machine has none).
Optional case fields: only ("darwin": run only on macOS, otherwise reported as SKIP),
needs ("bootvol": skipped when no /Volumes entry resolves to /).
Revision 3 cases (variables and the working directory judged by their possible values) carry the
tag r3:<spec item> and live in the groups r3v (variables) and r3c (working directory); a rule given as a
tuple means either report is acceptable (the spec does not say whether a name that was never assigned
before a possibly-skipped assignment is read as unknown or as empty). A case may be expected to be
allowed in revision 3 while revision 2 refused it: those rows carry a "revision 3" comment.
Revision 2 cases carry the tag r2:<spec item> (for example r2:1.1); a final check
asserts that every item has at least 3 entries with both an allow and a deny case
(items implemented as separate checks are listed in SPECIAL_ITEMS).

Hooks directory lookup: the environment variable RM_GUARD_HOOKS_DIR (made absolute) wins; otherwise
the sibling `../hooks` of this file's directory, then the parent of this file's directory; the first
directory containing block-recursive-rm.py is used.

Usage:
  rm-guard-cases.py [--direct] [--only PREFIX] [--jobs N] [--list]

Output: one `PASS id` / `FAIL id reason` / `SKIP id reason` line per case, then
`SUMMARY total pass fail skip` (exit code 1 when anything failed; skipped cases do
not count as failures).

Requires python 3.9+ (standard library only).
"""
import argparse
import concurrent.futures
import json
import os
import pwd
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK_NAME = "block-recursive-rm.py"


def _find_hooks_dir():
    env = os.environ.get("RM_GUARD_HOOKS_DIR")
    if env:
        return os.path.abspath(env)
    cands = [os.path.normpath(os.path.join(HERE, "..", "hooks")), os.path.normpath(os.path.join(HERE, ".."))]
    for c in cands:
        if os.path.isfile(os.path.join(c, HOOK_NAME)):
            return c
    return cands[0]


HOOKS = _find_hooks_dir()
HOOK_PATH = os.path.join(HOOKS, HOOK_NAME)
RUN_GUARD = os.path.join(HOOKS, "run-guard.sh")
CASE_TIMEOUT = 20
MAX_JOBS = 4
EXPANSION_PHRASE = "每次 Bash 工具调用都是新的 shell"
RULES = ("expansion", "tilde", "protected-path", "protected-glob", "unknown-cwd", "unparsable")

CASES = []
SPECIALS = []
_counters = {}


def _add(group, slug, cmd, expect, rule=None, cwd="work", target=None, tags=(), only=None, needs=None):
    _counters[group] = _counters.get(group, 0) + 1
    cid = "%s%02d-%s" % (group, _counters[group], slug)
    if expect == "deny":
        for _r in ((rule,) if isinstance(rule, str) else tuple(rule or ())):
            if _r not in RULES:
                raise ValueError("bad rule for %s: %r" % (cid, rule))
        if not rule:
            raise ValueError("bad rule for %s: %r" % (cid, rule))
    CASES.append({"id": cid, "group": group, "cmd": cmd, "expect": expect, "rule": rule,
                  "cwd": cwd, "target": target, "tags": (group,) + tuple(tags),
                  "only": only, "needs": needs})


def d(group, slug, cmd, rule, cwd="work", target=None, tags=()):
    _add(group, slug, cmd, "deny", rule, cwd, target, tags)


def a(group, slug, cmd, cwd="work", tags=()):
    _add(group, slug, cmd, "allow", None, cwd, None, tags)


# ---------------------------------------------------------------------------
# forms: spec section 1 item 2, every calling form (target "$X" -> expansion)
# ---------------------------------------------------------------------------
G = "forms"
for slug, cmd in [
    ("plain", 'rm -rf "$X"'),
    ("bin-rm", '/bin/rm -rf "$X"'),
    ("usr-bin-rm", '/usr/bin/rm -rf "$X"'),
    ("backslash-rm", '\\rm -rf "$X"'),
    ("squote-rm", "'rm' -rf \"$X\""),
    ("dquote-rm", '"rm" -rf "$X"'),
    ("grm", 'grm -rf "$X"'),
    ("command", 'command rm -rf "$X"'),
    ("exec", 'exec rm -rf "$X"'),
    ("sudo", 'sudo rm -rf "$X"'),
    ("sudo-opt", 'sudo -u root rm -rf "$X"'),
    ("doas", 'doas rm -rf "$X"'),
    ("doas-opt", 'doas -u root rm -rf "$X"'),
    ("env", 'env rm -rf "$X"'),
    ("env-i-assign", 'env -i FOO=1 BAR=2 rm -rf "$X"'),
    ("nice", 'nice rm -rf "$X"'),
    ("nice-n", 'nice -n 5 rm -rf "$X"'),
    ("nohup", 'nohup rm -rf "$X"'),
    ("time", 'time rm -rf "$X"'),
    ("timeout", 'timeout 10 rm -rf "$X"'),
    ("timeout-opt", 'timeout -k 5 10 rm -rf "$X"'),
    ("gtimeout", 'gtimeout 10 rm -rf "$X"'),
    ("caffeinate", 'caffeinate rm -rf "$X"'),
    ("caffeinate-opt", 'caffeinate -i rm -rf "$X"'),
    ("xargs", 'xargs rm -rf "$X"'),
    ("xargs-opt", 'xargs -n1 -P2 rm -rf "$X"'),
    ("parallel", 'parallel rm -rf "$X"'),
    ("parallel-opt", 'parallel -j2 rm -rf "$X"'),
    ("assign-prefix", 'FOO=1 rm -rf "$X"'),
    ("assign-prefix-two", 'FOO=1 BAR="a b" rm -rf "$X"'),
    ("layered", 'sudo env FOO=1 nice -n 5 rm -rf "$X"'),
    ("layered-2", 'FOO=1 nohup timeout 30 sudo -n env -i rm -rf "$X"'),
    ("compound-and", 'echo hi && rm -rf "$X"'),
    ("compound-semicolon", 'echo hi; rm -rf "$X"'),
    ("compound-or", 'false || rm -rf "$X"'),
    ("compound-pipe", 'true | rm -rf "$X"'),
    ("compound-newline", 'echo hi\nrm -rf "$X"'),
    ("compound-background", 'sleep 1 & rm -rf "$X"'),
    ("if-block", 'if true; then rm -rf "$X"; fi'),
    ("for-loop-var", 'for f in a b; do rm -rf "$f"; done'),
    ("brace-group", '{ rm -rf "$X"; }'),
    ("subshell", '( rm -rf "$X" )'),
]:
    d(G, slug, cmd, "expansion")

# ---------------------------------------------------------------------------
# opts: spec section 1 item 1 and "容易漏" 3 (option spellings)
# ---------------------------------------------------------------------------
G = "opts"
for slug, cmd in [
    ("r", 'rm -r "$X"'),
    ("R", 'rm -R "$X"'),
    ("recursive", 'rm --recursive "$X"'),
    ("rf", 'rm -rf "$X"'),
    ("fr", 'rm -fr "$X"'),
    ("Rf", 'rm -Rf "$X"'),
    ("rfv", 'rm -rfv "$X"'),
    ("vrf", 'rm -vrf "$X"'),
    ("split", 'rm -r -f "$X"'),
    ("split-v-r", 'rm -v -r "$X"'),
    ("long-both", 'rm --recursive --force "$X"'),
    ("dashdash", 'rm -fr -- "$X"'),
    ("after-path", 'rm "$X" -rf'),
    ("after-path-two", 'rm "$X" "$Y" -r'),
    ("I-r", 'rm -I -r "$X"'),
]:
    d(G, slug, cmd, "expansion", tags=("miss3",))
a(G, "plain-var", 'rm "$f"', tags=("ok3", "miss3"))
a(G, "force-var", 'rm -f "$X"', tags=("ok3", "miss3"))
a(G, "rmdir", 'rmdir "$d"', tags=("ok3", "miss3"))
a(G, "unlink", 'unlink "$f"', tags=("miss3",))
a(G, "rm-d", 'rm -d "$X"', tags=("miss3",))
a(G, "rm-i-v", 'rm -iv "$f"', tags=("miss3",))
a(G, "force-long", 'rm --force "$X"', tags=("miss3",))
a(G, "dashdash-r-is-name", 'rm -- -r "$f"', tags=("miss3",))
d(G, "dashdash-then-target-var", 'rm -r -- "$X" -f', "expansion", tags=("miss3",))
d(G, "no-preserve-root", "rm --no-preserve-root -rf /", "protected-path")

# ---------------------------------------------------------------------------
# find: find ... -delete / -exec rm
# ---------------------------------------------------------------------------
G = "find"
d(G, "var-delete", 'find "$X" -delete', "expansion", tags=("miss4",))
d(G, "home-var-name-delete", "find $HOME -name '*.tmp' -delete", "expansion")
d(G, "tilde-delete", "find ~ -delete", "tilde")
d(G, "realhome-delete", "find {REALHOME} -name x -delete", "protected-path")
d(G, "root-delete", "find / -name x -delete", "protected-path")
d(G, "users-delete", "find {REALHOME_PARENT} -name x -delete", "protected-path")  # 家目录的上层(macOS 上是 /Users)
d(G, "exec-rm-no-r", 'find "$X" -type f -exec rm {} \\;', "expansion")
d(G, "exec-rm-rf-plus", 'find "$X" -exec rm -rf {} +', "expansion")
d(G, "execdir-rm", 'find "$X" -execdir rm -rf {} \\;', "expansion")
d(G, "ok-rm", 'find "$X" -ok rm -r {} \\;', "expansion")
d(G, "cwd-home-dot-delete", "find . -name x -delete", "protected-path", cwd="home")
d(G, "second-start-var", 'find build "$X" -delete', "expansion")
d(G, "exec-rm-realhome", "find {REALHOME} -exec rm -rf {} +", "protected-path")
a(G, "literal-tmp-delete", "find /tmp/abc -name '*.o' -delete")
a(G, "rel-dot-delete", "find . -name '*.pyc' -delete")
a(G, "two-literal-starts", "find build dist -type f -delete")
a(G, "other-user-proj", "find /Users/zz-nobody-zz/proj -type f -delete")
a(G, "system-tmp-with-filter", "find /var/tmp -name 'x*' -mtime +7 -delete")  # /tmp 在 CI 里是测试家目录的上层,改用 /var/tmp
a(G, "var-without-delete", 'find "$X" -name x')
a(G, "var-exec-ls", 'find "$X" -exec ls {} \\;')
a(G, "var-exec-grep-rm-word", 'find "$X" -exec grep rm {} \\;')

# ---------------------------------------------------------------------------
# nest: nested text (-c strings, eval, substitutions, heredocs, ssh, trap, xargs/find sh -c)
# ---------------------------------------------------------------------------
G = "nest"
d(G, "bash-c", "bash -c 'rm -rf \"$HOME\"'", "expansion", tags=("miss4",))
d(G, "sh-c-dq", 'sh -c "rm -rf \\$HOME"', "expansion")
d(G, "bash-lc", "bash -lc 'rm -rf $X'", "expansion")
d(G, "zsh-ec", "zsh -ec 'rm -rf $X'", "expansion")
d(G, "dash-c", "dash -c 'rm -rf $X'", "expansion")
d(G, "ksh-c", "ksh -c 'rm -rf $X'", "expansion")
d(G, "bash-c-two-levels", "bash -c \"sh -c 'rm -rf \\$HOME'\"", "expansion", tags=("miss4",))
d(G, "bash-c-cd-home", "bash -c 'cd ~ && rm -rf *'", "protected-glob")
d(G, "eval-sq", "eval 'rm -rf \"$X\"'", "expansion")
d(G, "eval-dq", 'eval "rm -rf $X"', "expansion")
d(G, "cmdsubst", 'echo $(rm -rf "$X")', "expansion")
d(G, "backtick", 'echo `rm -rf "$X"`', "expansion")
d(G, "procsubst-in", 'cat <(rm -rf "$X")', "expansion")
d(G, "procsubst-out", 'tee >(rm -rf "$X")', "expansion")
d(G, "heredoc-bash", "bash <<'EOF'\nrm -rf \"$D\"\nEOF", "expansion", tags=("miss4",))
d(G, "heredoc-bash-unquoted", "bash <<EOF\nrm -rf \"$D\"\nEOF", "expansion")
d(G, "heredoc-sh", "sh <<'EOF'\necho hi\nrm -rf $D\nEOF", "expansion")
d(G, "heredoc-zsh", "zsh <<'EOF'\nrm -rf ~/x\nEOF", "tilde")
d(G, "heredoc-bash-s", "bash -s <<'EOF'\nrm -rf \"$D\"\nEOF", "expansion")
d(G, "heredoc-ssh", "ssh host <<'EOF'\nrm -rf \"$D\"\nEOF", "expansion")
d(G, "heredoc-ssh-unquoted", "ssh host <<EOF\nrm -rf ~/x\nEOF", "tilde")
d(G, "ssh-remote-var", "ssh host 'rm -rf $HOME/x'", "expansion", tags=("miss4",))
d(G, "ssh-remote-tilde", 'ssh -p 22 user@host "rm -rf ~/x"', "tilde")
d(G, "ssh-remote-generic-root", "ssh host 'rm -rf /home'", "protected-path")
d(G, "ssh-remote-usr", "ssh -i /tmp/k host 'rm -rf /usr'", "protected-path")
d(G, "trap-var", "trap 'rm -rf \"$X\"' EXIT", "expansion")
d(G, "trap-dq-multi-signal", 'trap "rm -rf \\$X" INT TERM', "expansion")
d(G, "xargs-sh-c", "echo a | xargs sh -c 'rm -rf \"$0\"'", "expansion", tags=("miss4",))
d(G, "xargs-opt-bash-c", "ls | xargs -I{} bash -c 'rm -rf \"$1\"' _ {}", "expansion")
d(G, "find-exec-sh-c", "find . -name x -exec sh -c 'rm -rf \"$1\"' _ {} \\;", "expansion")
d(G, "cmdsubst-in-arg-tilde", "echo $(echo hi; rm -rf ~)", "tilde")
d(G, "nested-in-compound", "ls && (bash -c 'rm -rf $X')", "expansion")
a(G, "bash-c-literal", "bash -c 'rm -rf /tmp/abc'")
a(G, "bash-c-echo-text", "bash -c 'echo rm -rf $HOME'")
a(G, "eval-literal", "eval 'rm -rf /tmp/abc'")
a(G, "cmdsubst-benign", 'echo $(date) && rm -rf /tmp/abc')
a(G, "heredoc-bash-benign", "bash <<'EOF'\necho hi\nEOF")
a(G, "heredoc-ssh-benign", "ssh host <<'EOF'\nls /tmp\nEOF")
a(G, "ssh-remote-literal", "ssh host 'rm -rf /home/deploy/app'")
a(G, "ssh-remote-relative", "ssh host 'rm -rf build'")
a(G, "ssh-remote-local-home-is-not-remote-home", "ssh host 'rm -rf {REALHOME}/x'")
a(G, "ssh-remote-echo-text", "ssh host 'echo rm -rf $HOME'")
a(G, "trap-literal", "trap 'rm -rf /tmp/abc' EXIT")
a(G, "xargs-sh-c-literal", "echo a | xargs sh -c 'echo $0'")
a(G, "find-exec-sh-c-literal", "find . -name x -exec sh -c 'ls \"$1\"' _ {} \\;")

# ---------------------------------------------------------------------------
# text: section 1 item 5, words that are not in command position
# ---------------------------------------------------------------------------
G = "text"
a(G, "echo-sq", "echo 'rm -rf $HOME'", tags=("ok3", "miss5"))
a(G, "grep-rm-rf", "grep -n 'rm -rf' a.txt", tags=("ok3", "miss5"))
a(G, "git-commit-msg", 'git commit -m "修 rm -rf \\$HOME 的问题"', tags=("ok3", "miss5"))
a(G, "comment-line", "# rm -rf $HOME", tags=("ok3", "miss5"))
a(G, "trailing-comment", 'echo hi # rm -rf "$HOME"', tags=("miss5",))
a(G, "echo-dq-escaped", 'echo "rm -rf \\$X"', tags=("miss5",))
a(G, "echo-unquoted-words", "echo rm -rf $HOME", tags=("miss5",))
a(G, "cat-heredoc-quoted", "cat > a.md <<'EOF'\nrm -rf \"$HOME\"\nEOF", tags=("ok3", "miss5"))
a(G, "cat-heredoc-unquoted", "cat > a.md <<EOF\n# 复盘\nrm -rf \"$HOME\" 把家目录删了\nEOF", tags=("miss5",))
a(G, "tee-heredoc", "tee notes.md <<'EOF'\nrm -rf $X\nEOF", tags=("miss5",))
a(G, "python-heredoc", "python3 - <<'EOF'\nprint('rm -rf \"$X\"')\nEOF", tags=("miss5",))
a(G, "printf-sq", "printf '%s\\n' 'rm -rf $HOME'", tags=("miss5",))
a(G, "git-log-grep", "git log --grep 'rm -rf $HOME'", tags=("miss5",))
a(G, "sed-pattern", "sed -n '/rm -rf/p' notes.md", tags=("miss5",))
a(G, "which-rm", "which rm", tags=("miss5",))
a(G, "ls-rm-named-file", "ls rm-guard-notes.md", tags=("miss5",))
a(G, "grep-dq-pattern", 'grep -rn "rm -rf" docs', tags=("miss5",))
a(G, "echo-redirect-doc", 'echo "rm -rf \\"\\$HOME\\"" >> notes.md', tags=("miss5",))
a(G, "heredoc-comment-lines", "cat <<'EOF' > guide.md\n# rm -rf ~\n$ rm -rf $X\nEOF", tags=("miss5",))
d(G, "command-after-doc-heredoc", "cat > a.md <<'EOF'\nrm -rf \"$HOME\"\nEOF\nrm -rf \"$X\"", "expansion", tags=("miss5",))
d(G, "command-after-git-commit", 'git commit -m "x" && rm -rf "$X"', "expansion", tags=("miss5",))

# ---------------------------------------------------------------------------
# exp: rule 1, expansion spellings ("容易漏" 2)
# ---------------------------------------------------------------------------
G = "exp"
for slug, cmd in [
    ("home", "rm -rf $HOME"),
    ("home-quoted", 'rm -rf "$HOME"'),
    ("home-braces", "rm -rf ${HOME}"),
    ("home-strip", 'rm -rf "${HOME%/}"'),
    ("default-root", 'rm -rf "${X:-/}"'),
    ("at-quoted", 'rm -rf "${@}"'),
    ("at", "rm -rf $@"),
    ("star", "rm -rf $*"),
    ("positional", "rm -rf $1"),
    ("middle", 'rm -rf "/a/$Y/b"'),
    ("suffix", "rm -rf /tmp/$X"),
    ("var-subpath", 'rm -rf "$X/sub"'),
    ("ansi-c", "rm -rf $'\\x2f'"),
    ("backtick", "rm -rf `echo /`"),
    ("cmdsubst", "rm -rf $(pwd)"),
    ("arith", "rm -rf $((1+1))"),
    ("required-form", 'rm -rf "${X:?}"'),
    ("tmpdir", 'rm -rf "$TMPDIR/foo"'),
    ("second-target", 'rm -rf build "$X"'),
    ("dq-with-sq-inside", "rm -rf \"it's $X\""),
]:
    d(G, slug, cmd, "expansion", tags=("miss2",))
a(G, "sq-home", "rm -rf '$HOME'", tags=("ok3", "miss2"))
a(G, "sq-subpath", "rm -rf '/tmp/$X'", tags=("miss2",))
a(G, "sq-braces", "rm -rf '${HOME}'", tags=("miss2",))
a(G, "no-recursive-var", 'rm -f "$X"', tags=("miss2",))
a(G, "rmdir-var", 'rmdir "$X"', tags=("miss2",))
d(G, "empty-var-slash-sub", 'rm -rf "$UNSET_RM_GUARD_PROBE/nonexistent-dir"', "expansion")

# ---------------------------------------------------------------------------
# mk: mktemp exception and its boundaries
# ---------------------------------------------------------------------------
G = "mk"
a(G, "basic", 'd=$(mktemp -d) && echo hi > "$d/x" && rm -rf "$d"', tags=("ok3",))
a(G, "trap", "tmp=$(mktemp -d); trap 'rm -rf \"$tmp\"' EXIT; cp a \"$tmp/\"", tags=("ok3",))
a(G, "backtick", 'd=`mktemp -d`; rm -rf "$d"', tags=("ok3",))
a(G, "export-fullpath-args", 'export T=$(/usr/bin/mktemp -d /tmp/foo.XXXXXX) && rm -rf "${T}/sub/dir"')
a(G, "declare-unquoted-target", "declare d=$(mktemp -d); rm -rf $d")
a(G, "readonly-quoted-assign", 'readonly d="$(mktemp -d)"; rm -rf "$d"')
a(G, "local-braces", 'local d=$(mktemp -d) ; rm -rf "${d}"')
a(G, "subpath-literal", 'd=$(mktemp -d); rm -rf "$d/build/out"')
a(G, "separate-statements", 'd=$(mktemp -d)\ncp a "$d"\nrm -rf "$d"')
d(G, "reassigned", 'd=$(mktemp -d); d=/; rm -rf "$d"', "protected-path")  # revision 1: d=/ is a literal assignment, "/" is protected
d(G, "reassigned-from-var", 'd=$(mktemp -d); d=$HOME; rm -rf "$d"', "expansion")
d(G, "unset", 'd=$(mktemp -d); unset d; rm -rf "$d"', "expansion")
d(G, "subpath-dotdot", 'd=$(mktemp -d); rm -rf "$d/../x"', "expansion")
d(G, "subpath-dotdot-end", 'd=$(mktemp -d); rm -rf "$d/.."', "expansion")
d(G, "subpath-glob-unquoted", "d=$(mktemp -d); rm -rf $d/*", "expansion")
d(G, "subpath-glob-in-quotes", 'd=$(mktemp -d); rm -rf "$d/*"', "expansion")
d(G, "subpath-other-var", 'd=$(mktemp -d); rm -rf "$d/$e"', "expansion")
d(G, "subpath-cmdsubst", 'd=$(mktemp -d); rm -rf "$d/$(whoami)"', "expansion")
d(G, "assigned-after-rm", 'rm -rf "$d"; d=$(mktemp -d)', "expansion")
d(G, "other-name", 'd=$(mktemp -d); rm -rf "$e"', "expansion")
d(G, "not-mktemp", 'd=$(echo /tmp/x); rm -rf "$d"', "expansion")
d(G, "param-expansion-form", 'd=$(mktemp -d); rm -rf "${d%/}"', "expansion")
d(G, "suffix-without-slash", 'd=$(mktemp -d); rm -rf "$d"x', "expansion")
d(G, "second-target-var", 'd=$(mktemp -d); rm -rf "$d" "$HOME"', "expansion")
d(G, "trap-after-reassign", "tmp=$(mktemp -d); tmp=/; trap 'rm -rf \"$tmp\"' EXIT", "protected-path")  # revision 1
d(G, "tmpdir-variable", 'rm -rf "$TMPDIR/x"', "expansion")
d(G, "for-loop-var", 'd=$(mktemp -d); for f in a b; do rm -rf "$f"; done', "expansion")

# ---------------------------------------------------------------------------
# tilde: rule 2
# ---------------------------------------------------------------------------
G = "tilde"
for slug, cmd in [
    ("bare", "rm -rf ~"),
    ("slash", "rm -rf ~/"),
    ("sub", "rm -rf ~/proj"),
    ("dot-dir", "rm -rf ~/.cache/x"),
    ("user", "rm -rf ~root"),
    ("user-sub", "rm -rf ~root/x"),
    ("dquote", 'rm -rf "~"'),
    ("squote", "rm -rf '~'"),
    ("dquote-sub", 'rm -rf "~/x"'),
    ("second-target", "rm -rf build ~/x"),
    ("plus", "rm -rf ~+"),
    ("ssh-remote", "ssh host 'rm -rf ~'"),
]:
    d(G, slug, cmd, "tilde")
a(G, "tilde-not-leading", "rm -rf build~")
a(G, "tilde-inside-name", "rm -rf /tmp/a~b")
a(G, "tilde-no-recursive", "rm -f ~/x")
a(G, "tilde-echo", "echo rm -rf ~")

# ---------------------------------------------------------------------------
# path: rule 3, literal protected locations (and their aliases)
# ---------------------------------------------------------------------------
G = "path"
for slug, cmd in [
    ("root", "rm -rf /"),
    ("root-double", "rm -rf //"),
    ("root-dot", "rm -rf /."),
    ("root-dotdot", "rm -rf /.."),
    ("tmp-dotdot", "rm -rf /tmp/.."),
    ("data-volume-root", "rm -rf /System/Volumes/Data"),
    ("data-volume-users", "rm -rf /System/Volumes/Data/Users"),
    ("users", "rm -rf /Users"),
    ("users-slash", "rm -rf /Users/"),
    ("system", "rm -rf /System"),
    ("library", "rm -rf /Library"),
    ("applications", "rm -rf /Applications"),
    ("volumes", "rm -rf /Volumes"),
    ("usr", "rm -rf /usr"),
    ("usr-local", "rm -rf /usr/local"),
    ("bin", "rm -rf /bin"),
    ("sbin", "rm -rf /sbin"),
    ("etc", "rm -rf /etc"),
    ("private-etc", "rm -rf /private/etc"),
    ("var", "rm -rf /var"),
    ("private-var", "rm -rf /private/var"),
    ("tmp", "rm -rf /tmp"),
    ("private-tmp-slash", "rm -rf /private/tmp/"),
    ("opt", "rm -rf /opt"),
    ("opt-homebrew", "rm -rf /opt/homebrew"),
    ("private", "rm -rf /private"),
    ("dev", "rm -rf /dev"),
    ("cores", "rm -rf /cores"),
    ("home-dir", "rm -rf /home"),
    ("root-dir", "rm -rf /root"),
    ("boot", "rm -rf /boot"),
    ("lib", "rm -rf /lib"),
    ("lib64", "rm -rf /lib64"),
    ("proc", "rm -rf /proc"),
    ("sys", "rm -rf /sys"),
    ("srv", "rm -rf /srv"),
    ("mnt", "rm -rf /mnt"),
    ("media", "rm -rf /media"),
    ("snap", "rm -rf /snap"),
    ("nix", "rm -rf /nix"),
    ("quoted", 'rm -rf "/Users"'),
    ("dotdot-from-sub", "rm -rf /usr/local/.."),
    ("redundant-slashes", "rm -rf //usr///local//"),
    ("tmp-dotdot-in-name", "rm -rf /tmp/abc/../.."),
    ("sudo", "sudo rm -rf /etc"),
    ("relative-dotdot-from-work", "rm -rf .."),
    ("home-env", "rm -rf {HOME}"),
    ("home-env-dotdot", "rm -rf {HOME}/.."),
    ("home-env-sub-dotdot", "rm -rf {HOME}/proj/../.."),
    ("work-dotdot-is-home-parent", "rm -rf {WORK}/.."),
]:
    d(G, slug, cmd, "protected-path")
a(G, "tmp-sub", "rm -rf /tmp/abc", tags=("ok3",))
a(G, "private-tmp-sub", "rm -rf /private/tmp/abc")
a(G, "var-tmp-sub", "rm -rf /var/tmp/abc")
a(G, "usr-local-sub", "rm -rf /usr/local/lib/foo")
a(G, "opt-sub", "rm -rf /opt/foo")
a(G, "library-sub", "rm -rf /Library/Caches/foo")
a(G, "applications-sub", "rm -rf /Applications/Foo.app")
a(G, "other-user-project", "rm -rf /Users/zz-nobody-zz/proj/x/.worktrees/foo", tags=("ok3",))
a(G, "home-env-sub", "rm -rf {HOME}/proj/x")
a(G, "realhome-sub-worktree", "rm -rf {REALHOME}/proj/x/.worktrees/foo", tags=("ok3",))
a(G, "relative-literals", "rm -rf ./build dist node_modules", tags=("ok3",))
a(G, "relative-dotdot-sub", "rm -rf ../work/build")
a(G, "tmp-dotdot-sub", "rm -rf /tmp/abc/../def")
a(G, "no-recursive-system", "rm -f /etc/foo.conf")
a(G, "rmdir-system", "rmdir /tmp")

# ---------------------------------------------------------------------------
# home: real home directory aliases ("容易漏" 1), pwd-recorded home
# ---------------------------------------------------------------------------
G = "home"
for slug, cmd in [
    ("plain", "rm -rf {REALHOME}"),
    ("slash", "rm -rf {REALHOME}/"),
    ("dot", "rm -rf {REALHOME}/."),
    ("data-volume", "rm -rf /System/Volumes/Data{REALHOME}"),
    ("data-volume-slash", "rm -rf /System/Volumes/Data{REALHOME}/"),
    ("double-slash", "rm -rf {REALHOME_DSLASH}"),
    ("trailing-double-slash", "rm -rf {REALHOME}//"),
    ("sub-dotdot", "rm -rf {REALHOME}/x/.."),
    ("parent", "rm -rf {REALHOME_PARENT}"),
    ("parent-slash", "rm -rf {REALHOME_PARENT}/"),
    ("quoted", 'rm -rf "{REALHOME}"'),
    ("dashdash", "rm -rf -- {REALHOME}"),
    ("sudo", "sudo rm -rf {REALHOME}"),
    ("private-var-dotdot", "rm -rf /private/var/.."),
    ("no-cwd", "rm -rf {REALHOME}"),
]:
    d(G, slug, cmd, "protected-path", cwd=("none" if slug == "no-cwd" else "work"), tags=("miss1",))
d(G, "glob-in-home", "rm -rf {REALHOME}/*", "protected-glob", tags=("miss1",))
d(G, "dotglob-in-home", "rm -rf {REALHOME}/.*", "protected-glob", tags=("miss1",))
d(G, "data-volume-glob", "rm -rf /System/Volumes/Data{REALHOME}/*", "protected-glob", tags=("miss1",))
d(G, "cwd-realhome-dot", "rm -rf .", "protected-path", cwd="{REALHOME}", tags=("miss1",))
d(G, "cwd-realhome-glob", "rm -rf *", "protected-glob", cwd="{REALHOME}", tags=("miss1",))
a(G, "sub-of-realhome", "rm -rf {REALHOME}/proj/build", tags=("miss1",))
a(G, "sub-of-realhome-data-volume", "rm -rf /System/Volumes/Data{REALHOME}/proj/build", tags=("miss1",))
a(G, "realhome-no-recursive", "rm -f {REALHOME}/x.txt", tags=("miss1",))

# ---------------------------------------------------------------------------
# glob: rule 4
# ---------------------------------------------------------------------------
G = "glob"
for slug, cmd, cwd in [
    ("root-star", "rm -rf /*", "work"),
    ("users-star", "rm -rf /Users/*", "work"),
    ("users-dotstar", "rm -rf /Users/.*", "work"),
    ("realhome-star", "rm -rf {REALHOME}/*", "work"),
    ("realhome-dotstar", "rm -rf {REALHOME}/.*", "work"),
    ("realhome-mid-glob", "rm -rf {REALHOME}/*/build", "work"),
    ("tmp-star", "rm -rf /tmp/*", "work"),
    ("etc-question", "rm -rf /etc/?", "work"),
    ("usr-bracket", "rm -rf /usr/[a-z]*", "work"),
    ("data-volume-star", "rm -rf /System/Volumes/Data/*", "work"),
    ("cwd-home-star", "rm -rf *", "home"),
    ("cwd-home-dotstar", "rm -rf .*", "home"),
    ("cwd-home-dot-star", "rm -rf ./*", "home"),
    ("cwd-home-bracket", "rm -rf [a-z]*", "home"),
    ("cwd-home-question", "rm -rf ?", "home"),
    ("cwd-home-sub-dotdot-star", "rm -rf ../*", "{HOME}/proj"),
    ("sudo-star", "sudo rm -rf /*", "work"),
    ("brace-includes-protected", "rm -rf /{usr,tmp}/*", "work"),
]:
    d(G, slug, cmd, "protected-glob", cwd=cwd)
d(G, "brace-expands-to-protected-literal", "rm -rf {/tmp,/etc}", "protected-path")
d(G, "brace-expands-first-hit-second", "rm -rf /tmp/x {/tmp/y,/Users}", "protected-path")
d(G, "brace-root-prefix", "rm -rf /{usr,Users}", "protected-path")
a(G, "brace-safe", "rm -rf /tmp/{a,b}")
a(G, "brace-safe-users-sub", "rm -rf /Users/{zz-a,zz-b}")
a(G, "tmp-sub-star", "rm -rf /tmp/abc/*")
a(G, "work-build-star", "rm -rf {WORK}/build/*")
a(G, "rel-build-glob", "rm -rf ./build/*.o")
a(G, "cwd-work-star", "rm -rf *", "work")
a(G, "cwd-work-dot-star", "rm -rf ./*", "work")
a(G, "quoted-star-literal-name", "rm -rf '{REALHOME}/*'")
a(G, "quoted-star-dq", 'rm -rf "/Users/*"')
a(G, "star-no-recursive", "rm -f /tmp/*")

# ---------------------------------------------------------------------------
# cwd: rule 5, working directory handling
# ---------------------------------------------------------------------------
G = "cwd"
d(G, "home-star", "rm -rf *", "protected-glob", cwd="home")
d(G, "home-dot", "rm -rf .", "protected-path", cwd="home")
d(G, "home-dot-slash", "rm -rf ./", "protected-path", cwd="home")
d(G, "cd-noarg-star", "cd; rm -rf *", "protected-glob")  # revision 3 item 2.3: after ";" the cwd is {old cwd} + {home}; home is protected (revision 2 had unknown-cwd)
d(G, "cd-noarg-and", "cd && rm -rf *", "protected-glob")
d(G, "cd-tilde-dot", "cd ~ && rm -rf .", "protected-path")
d(G, "cd-tilde-star", "cd ~ && rm -rf *", "protected-glob")
d(G, "cd-tilde-slash-star", "cd ~/ && rm -rf ./*", "protected-glob")
d(G, "pushd-tilde-star", "pushd ~ >/dev/null; rm -rf *", "protected-glob")  # revision 3 item 2.3: {old cwd} + {home} (revision 2 had unknown-cwd)
d(G, "subshell-cd-home", "(cd ~ && rm -rf *)", "protected-glob")
d(G, "cd-home-env-literal-star", "cd {HOME} && rm -rf *", "protected-glob")
d(G, "cd-dotdot-from-work", "cd .. && rm -rf *", "protected-glob")
d(G, "cd-sibling-home-star", "cd ../home && rm -rf *", "protected-glob")
d(G, "cd-sub-then-dotdot", "cd {HOME}/proj && rm -rf ..", "protected-path")
d(G, "cd-var-dot-slash-star", 'cd "$X" && rm -rf ./*', "unknown-cwd")
d(G, "cd-var-dot", "cd $X; rm -rf .", "unknown-cwd")
d(G, "cd-var-dotdot", 'cd "$X" && rm -rf ..', "unknown-cwd")
d(G, "cd-var-star", 'cd "$X" && rm -rf *', "unknown-cwd")
d(G, "cd-var-dotstar", 'cd "$X" && rm -rf .*', "unknown-cwd")
d(G, "cd-var-dotdot-sub", 'cd "$X" && rm -rf ../x', "unknown-cwd")
d(G, "cd-dash-star", "cd - && rm -rf *", "unknown-cwd")
d(G, "subshell-cd-var", '(cd "$X" && rm -rf ./*)', "unknown-cwd")
d(G, "none-dot", "rm -rf .", "unknown-cwd", cwd="none")
d(G, "none-dot-slash", "rm -rf ./", "unknown-cwd", cwd="none")
d(G, "none-dotdot", "rm -rf ..", "unknown-cwd", cwd="none")
d(G, "none-dotdot-sub", "rm -rf ../x", "unknown-cwd", cwd="none")
d(G, "none-star", "rm -rf *", "unknown-cwd", cwd="none")
d(G, "none-dotstar", "rm -rf .*", "unknown-cwd", cwd="none")
d(G, "none-dot-star", "rm -rf ./*", "unknown-cwd", cwd="none")
d(G, "relative-cwd-dot", "rm -rf .", "unknown-cwd", cwd="relative")
d(G, "relative-cwd-star", "rm -rf *", "unknown-cwd", cwd="relative")
d(G, "none-after-cd-var", 'cd "$X"; rm -rf ../y', "unknown-cwd", cwd="none")
a(G, "work-star", "rm -rf *", cwd="work")
a(G, "work-dot-star", "rm -rf ./*", cwd="work")
a(G, "work-build", "rm -rf build", cwd="work")
a(G, "cd-literal-build", "cd /tmp/proj && rm -rf build")
a(G, "cd-literal-build-pushd", "pushd {WORK} >/dev/null && rm -rf build dist")
a(G, "cd-literal-star", "cd /tmp/proj && rm -rf *")
a(G, "cd-relative-star", "cd sub && rm -rf *", cwd="work")
a(G, "cd-tilde-sub-star", "cd ~/zz-proj && rm -rf *")
a(G, "cd-var-then-named", 'cd "$X" && rm -rf build')
a(G, "cd-var-then-dot-name", 'cd "$X" && rm -rf ./dist')
a(G, "cd-dash-named", "cd - && rm -rf node_modules")
a(G, "home-build", "rm -rf build", cwd="home")
a(G, "home-dot-build", "rm -rf ./build/", cwd="home")
a(G, "none-build", "rm -rf build", cwd="none")
a(G, "none-dot-named", "rm -rf ./dist node_modules", cwd="none")
a(G, "relative-cwd-build", "rm -rf build", cwd="relative")
a(G, "subdir-cwd-star", "rm -rf *", cwd="{WORK}/sub")
a(G, "cd-home-sub-literal", "cd {HOME}/proj && rm -rf build")

# ---------------------------------------------------------------------------
# unp: rule 6, unparsable input falls back to text rules
# ---------------------------------------------------------------------------
G = "unp"
d(G, "unclosed-dq-var", 'rm -rf "$HOME', "unparsable")
d(G, "unclosed-sq-tilde", "rm -rf ~ 'abc", "unparsable")
d(G, "unclosed-in-echo-with-rm", 'echo "oops; rm -rf $X', "unparsable")
d(G, "unclosed-find-delete", "find $X -delete 'abc", "unparsable")
d(G, "unclosed-backtick", "rm -rf `echo /", "unparsable")
d(G, "unclosed-after-tilde-target", 'rm -rf ~/x "', "unparsable")
_deep = 'rm -rf "$X"'
for _i in range(10):
    _deep = "echo $(" + _deep + ")"
d(G, "nesting-deeper-than-8", _deep, "unparsable")
a(G, "unclosed-no-markers", "rm -rf /tmp/x 'abc")
a(G, "unclosed-relative-no-markers", 'rm -r build "oops')
a(G, "unclosed-no-rm", 'echo "unclosed $HOME')
a(G, "unclosed-no-recursive", 'rm -f "$X')
a(G, "unclosed-rmdir", 'rmdir "$d')

# ---------------------------------------------------------------------------
# order: several targets, leftmost hit is reported
# ---------------------------------------------------------------------------
G = "order"
d(G, "var-before-tilde", 'rm -rf /tmp/ok "$X" ~', "expansion", target="$X")
d(G, "tilde-before-var", 'rm -rf ~ "$X"', "tilde", target="~")
d(G, "path-before-var", 'rm -rf /tmp/a /Users "$X"', "protected-path", target="/Users")
d(G, "second-segment-after-first", 'rm -rf "$X"; rm -rf ~', "expansion", target="$X")
d(G, "second-segment-hit", "rm -rf /tmp/ok; rm -rf ~/x", "tilde", target="~/x")
d(G, "literal-then-system", "rm -rf ./build /etc", "protected-path", target="/etc")
d(G, "glob-before-tilde", "rm -rf /tmp/ok /* ~", "protected-glob", target="/*")
d(G, "outer-before-nested", "rm -rf ~ ; bash -c 'rm -rf $X'", "tilde", target="~")

# ---------------------------------------------------------------------------
# ok3: spec section 3 allow examples that are not already in another group
# ---------------------------------------------------------------------------
G = "ok3"
a(G, "tmp-abc", "rm -rf /tmp/abc")
a(G, "relative-trio", "rm -rf ./build dist node_modules")
a(G, "worktree-path", "rm -rf /Users/zz-nobody-zz/proj/x/.worktrees/foo")
a(G, "mktemp-and-chain", 'd=$(mktemp -d) && echo hi > "$d/x" && rm -rf "$d"')
a(G, "mktemp-trap", "tmp=$(mktemp -d); trap 'rm -rf \"$tmp\"' EXIT; cp a \"$tmp/\"")
a(G, "rm-f-var", 'rm -f "$X"')
a(G, "rm-var", 'rm "$f"')
a(G, "rmdir-var", 'rmdir "$d"')
a(G, "sq-home-name", "rm -rf '$HOME'")
a(G, "echo-text", "echo 'rm -rf $HOME'")
a(G, "grep-text", "grep -n 'rm -rf' a.txt")
a(G, "git-commit-text", 'git commit -m "修 rm -rf \\$HOME 的问题"')
a(G, "comment-text", "# rm -rf $HOME")
a(G, "doc-heredoc-text", "cat > a.md <<'EOF'\nrm -rf \"$HOME\"\nEOF")



# ---------------------------------------------------------------------------
# lit: revision 1 item 1, literal assignment exception (NAME=<literal path> before the rm)
# ---------------------------------------------------------------------------
G = "lit"
for slug, cmd, cwd, *_flip in [
    ("abs-dq", 'D=/tmp/x; rm -rf "$D"', "work"),
    ("abs-bare", 'D=/tmp/x; rm -rf $D', "work"),
    ("abs-braces", 'D=/tmp/x; rm -rf ${D}', "work"),
    ("abs-braces-dq", 'D=/tmp/x; rm -rf "${D}"', "work"),
    ("assign-dq-value", 'D="/tmp/a b"; rm -rf "$D"', "work"),
    ("assign-sq-value", "D='/tmp/x'; rm -rf \"$D\"", "work"),
    ("and-chain", 'D=/tmp/x && rm -rf "$D"', "work"),
    ("newline", 'D=/tmp/x\nrm -rf "$D"', "work"),
    ("export", 'export D=/tmp/x; rm -rf "$D"', "work"),
    ("local", 'local D=/tmp/x; rm -rf "$D"', "work"),
    ("declare", 'declare D=/tmp/x; rm -rf "$D"', "work"),
    ("readonly", 'readonly D=/tmp/x; rm -rf "$D"', "work"),
    ("export-quoted", 'export D="/tmp/x"; rm -rf "$D"', "work"),
    ("subpath-dq", 'D=/tmp/x; rm -rf "$D/sub/dir"', "work"),
    ("subpath-bare", 'D=/tmp/x; rm -rf $D/sub', "work"),
    ("subpath-braces", 'D=/tmp/x; rm -rf "${D}/sub"', "work"),
    ("subpath-glob", 'D=/tmp/x; rm -rf $D/*', "work"),
    ("subpath-glob-suffix", 'D=/tmp/x; rm -rf $D/*.o', "work"),
    ("rel-name", 'D=build; rm -rf "$D"', "work"),
    ("rel-dot-name", 'D=./build; rm -rf "$D"', "work"),
    ("rel-subpath-glob", 'D=sub; rm -rf $D/*', "work"),
    ("rel-dotdot-sibling", 'D=../out; rm -rf "$D"', "work"),
    ("rel-from-home-named", 'D=build; rm -rf "$D"', "home"),
    ("rel-after-cd", 'cd /tmp/p && D=out; rm -rf "$D"', "work"),  # revision 3 item 1.3: D is {empty, /tmp/p/out}; quoted empty is harmless (revision 2 had expansion)
    ("rel-unknown-cwd-named", 'cd "$X"; D=build; rm -rf "$D"', "work"),
    ("rel-no-cwd-named", 'D=build; rm -rf "$D"', "none"),
    ("work-placeholder-glob", 'D={WORK}/out; rm -rf $D/*', "work"),
    ("system-subpath", 'D=/usr; rm -rf "$D/lib"', "work"),
    ("case-branches", 'case "$1" in a) D=/tmp/a;; *) D=/tmp/b;; esac; rm -rf "$D"', "work"),  # revision 3 item 1.3: D is {empty, /tmp/a, /tmp/b}, all harmless (revision 2 had expansion)
    ("if-else", 'if [ -n "$Q" ]; then D=/tmp/a; else D=/tmp/b; fi; rm -rf "$D"', "work"),  # revision 3 item 1.3 (revision 2 had expansion)
    ("two-names", 'D=/tmp/x; E=/tmp/y; rm -rf "$D" "$E"', "work"),
    ("rm-flag-forms", 'D=/tmp/x; rm -fr -- "$D"', "work"),
    ("sudo-form", 'D=/tmp/x; sudo rm -rf "$D"', "work"),
    ("nested-bash-c", "bash -c 'D=/tmp/x; rm -rf \"$D\"'", "work"),
    ("assigned-after-rm-is-fine", 'D=/tmp/x; rm -rf "$D"; D=$HOME', "work"),
    ("trap-literal", "D=/tmp/x; trap 'rm -rf \"$D\"' EXIT", "work"),  # ambiguity: spec names trap only for mktemp
]:
    if _flip:
        d(G, slug, cmd, _flip[0], cwd=cwd)
    else:
        a(G, slug, cmd, cwd=cwd)

# protected values, reported with the rule the substituted path hits
for slug, cmd, rule, cwd in [
    ("val-root", 'D=/; rm -rf "$D"', "protected-path", "work"),
    ("val-realhome", 'D={REALHOME}; rm -rf "$D"', "protected-path", "work"),
    ("val-realhome-slash", 'D={REALHOME}/; rm -rf "$D"', "protected-path", "work"),
    ("val-realhome-dotdot", 'D={REALHOME}/x/..; rm -rf "$D"', "protected-path", "work"),
    ("val-realhome-parent", 'D={REALHOME_PARENT}; rm -rf "$D"', "protected-path", "work"),
    ("val-datavolume-home", 'D=/System/Volumes/Data{REALHOME}; rm -rf "$D"', "protected-path", "work"),
    ("val-subprocess-home", 'D={HOME}; rm -rf "$D"', "protected-path", "work"),
    ("val-usr", 'D=/usr; rm -rf "$D"', "protected-path", "work"),
    ("val-etc-braces", 'D=/etc; rm -rf "${D}"', "protected-path", "work"),
    ("val-users-export", 'export D=/Users; rm -rf "$D"', "protected-path", "work"),
    ("val-system-sub-is-system", 'D=/usr; rm -rf "$D/local"', "protected-path", "work"),
    ("val-private-tmp", 'D=/private/tmp; rm -rf "$D"', "protected-path", "work"),
    ("val-rel-dotdot-to-home-parent", 'D=..; rm -rf "$D"', "protected-path", "work"),
    ("val-rel-dot-in-home", 'D=.; rm -rf "$D"', "protected-path", "home"),
    ("val-glob-root", 'D=/; rm -rf $D/*', "protected-glob", "work"),
    ("val-glob-realhome", 'D={REALHOME}; rm -rf $D/*', "protected-glob", "work"),
    ("val-glob-home-dotstar", 'D={HOME}; rm -rf $D/.*', "protected-glob", "work"),
    ("val-glob-tmp", 'D=/tmp; rm -rf $D/*', "protected-glob", "work"),
    ("val-rel-unknown-cwd-dotdot", 'cd "$X"; D=..; rm -rf "$D"', "unknown-cwd", "work"),
    ("val-rel-no-cwd-dot", 'D=.; rm -rf "$D"', "unknown-cwd", "none"),
    # literal-assignment exception does not apply -> expansion
    # revision 3 item 1.5: an empty value is {empty}: quoted "$D" is an empty argument (harmless), "$D/x" is /x (not protected)
    ("na-empty", 'D=; rm -rf "$D"', None, "work"),
    ("na-empty-dq", 'D=""; rm -rf "$D"', None, "work"),
    ("na-empty-subpath", 'D=""; rm -rf "$D/x"', None, "work"),
    ("na-tilde-value", 'D=~/x; rm -rf "$D"', "expansion", "work"),
    ("na-tilde-quoted-value", 'D="~/x"; rm -rf "$D"', "expansion", "work"),
    ("na-value-dollar-var", 'D=$HOME/x; rm -rf "$D"', "expansion", "work"),
    ("na-value-dollar-braces", 'D="${HOME}/x"; rm -rf "$D"', "expansion", "work"),
    ("na-value-cmdsubst", 'D="$(cat f)"; rm -rf "$D"', "expansion", "work"),
    ("na-value-cmdsubst-bare", 'D=$(cat f); rm -rf "$D"', "expansion", "work"),
    ("na-value-backtick", 'D=`cat f`; rm -rf "$D"', "expansion", "work"),
    ("na-value-glob-star", 'D=/tmp/*; rm -rf "$D"', "expansion", "work"),
    ("na-value-glob-question", 'D=/tmp/x?; rm -rf "$D"', "expansion", "work"),
    ("na-value-glob-bracket", 'D=/tmp/x[ab]; rm -rf "$D"', "expansion", "work"),
    ("na-chain", 'A=/tmp/x; B="$A/y"; rm -rf "$B"', "expansion", "work"),
    ("na-chain-bare", 'A=/tmp/x; B=$A/y; rm -rf $B', "expansion", "work"),
    ("na-after-rm", 'rm -rf "$D"; D=/tmp/x', "expansion", "work"),
    ("na-reassigned-cmdsubst", 'D=/tmp/x; D=$(cat f); rm -rf "$D"', "expansion", "work"),
    ("na-reassigned-var", 'D=/tmp/x; D=$HOME; rm -rf "$D"', "expansion", "work"),
    ("na-unset", 'D=/tmp/x; unset D; rm -rf "$D"', "expansion", "work"),
    ("na-unset-subpath", 'D=/tmp/x; unset D; rm -rf "$D/sub"', "expansion", "work"),
    ("na-subpath-dotdot", 'D=/tmp/x; rm -rf "$D/../y"', "expansion", "work"),
    ("na-subpath-dotdot-end", 'D=/tmp/x; rm -rf "$D/.."', "expansion", "work"),
    ("na-subpath-other-var", 'D=/tmp/x; rm -rf "$D/$E"', "expansion", "work"),
    ("na-subpath-cmdsubst", 'D=/tmp/x; rm -rf "$D/$(whoami)"', "expansion", "work"),
    ("na-letter-after-name", 'D=/tmp/x; rm -rf $Dy', "expansion", "work"),
    ("na-letter-after-braced-name", 'D=/tmp/x; rm -rf "${D}"y', "expansion", "work"),
    ("na-letter-after-quoted-name", 'D=/tmp/x; rm -rf "$D"y', "expansion", "work"),
    ("na-other-name", 'D=/tmp/x; rm -rf "$E"', "expansion", "work"),
    ("na-param-expansion", 'D=/tmp/x; rm -rf "${D%/}"', "expansion", "work"),
    ("na-default-form", 'D=/tmp/x; rm -rf "${D:-/}"', "expansion", "work"),
    ("na-second-target-unset", 'D=/tmp/x; rm -rf "$D" "$HOME"', "expansion", "work"),
    ("na-for-loop", 'D=/tmp/x; for f in a b; do rm -rf "$f"; done', "expansion", "work"),
    ("na-trap-reassigned", "D=/tmp/x; D=; trap 'rm -rf \"$D\"' EXIT", None, "work"),  # revision 3 item 1.5: empty quoted target is harmless
    ("na-nested-after-rm", "bash -c 'rm -rf \"$D\"; D=/tmp/x'", "expansion", "work"),
]:
    if rule is None:
        a(G, slug, cmd, cwd=cwd)
    else:
        d(G, slug, cmd, rule, cwd=cwd)

# ---------------------------------------------------------------------------
# hdp: revision 1 item 2, heredoc piped into a shell (no -c) is judged as nested text
# ---------------------------------------------------------------------------
G = "hdp"
d(G, "cat-bash", 'cat <<EOF | bash\nrm -rf "$X"\nEOF', "expansion")
d(G, "cat-sh-s-quoted", "cat <<'EOF' | sh -s\nrm -rf \"$X\"\nEOF", "expansion")
d(G, "cat-zsh", 'cat <<EOF | zsh\nrm -rf "$X"\nEOF', "expansion")
d(G, "cat-dash", "cat <<'EOF' | dash\nrm -rf $X\nEOF", "expansion")
d(G, "cat-ksh", "cat <<'EOF' | ksh\nrm -rf $X\nEOF", "expansion")
d(G, "cat-bash-s", "cat <<'EOF' | bash -s\nrm -rf \"$X\"\nEOF", "expansion")
d(G, "cat-bash-tilde", "cat <<'EOF' | bash\nrm -rf ~/x\nEOF", "tilde")
d(G, "cat-bash-protected", "cat <<'EOF' | bash\nrm -rf /usr\nEOF", "protected-path")
d(G, "cat-bash-second-line", "cat <<'EOF' | bash\necho hi\nrm -rf \"$X\"\nEOF", "expansion")
d(G, "cat-bash-then-more", "cat <<'EOF' | bash && echo done\nrm -rf \"$X\"\nEOF", "expansion")
a(G, "cat-bash-literal", "cat <<EOF | bash\nrm -rf /tmp/abc\nEOF")
a(G, "cat-sh-s-literal", "cat <<'EOF' | sh -s\nrm -rf /tmp/abc ./build\nEOF")
a(G, "cat-zsh-literal", "cat <<EOF | zsh\nrm -rf /tmp/abc\nEOF")
a(G, "cat-bash-benign", "cat <<'EOF' | bash\necho hi\nEOF")
a(G, "cat-bash-mktemp", "cat <<'EOF' | bash\nd=$(mktemp -d); rm -rf \"$d\"\nEOF")
a(G, "cat-bash-literal-assign", "cat <<'EOF' | bash\nD=/tmp/x; rm -rf \"$D\"\nEOF")
a(G, "cat-bash-non-recursive", "cat <<'EOF' | bash\nrm -f \"$X\"\nEOF")
a(G, "cat-bash-echo-text", "cat <<'EOF' | bash\necho 'rm -rf $HOME'\nEOF")
a(G, "cat-tee-md", 'cat <<EOF | tee a.md\nrm -rf "$X"\nEOF')
a(G, "cat-tee-md-quoted", "cat <<'EOF' | tee a.md\nrm -rf \"$HOME\"\nEOF")
a(G, "cat-python3", 'cat <<EOF | python3\nrm -rf "$X"\nEOF')
a(G, "cat-cat", "cat <<'EOF' | cat\nrm -rf \"$X\"\nEOF")
a(G, "cat-bash-c-ignores-stdin", "cat <<'EOF' | bash -c 'echo hi'\nrm -rf \"$X\"\nEOF")
a(G, "cat-redirect-file", "cat <<'EOF' > cleanup.sh\nrm -rf \"$X\"\nEOF")
a(G, "cat-grep", "cat <<'EOF' | grep rm\nrm -rf \"$X\"\nEOF")

# ---------------------------------------------------------------------------
# ovar: revision 1 item 3, recursive option may arrive through an unquoted expansion
# ---------------------------------------------------------------------------
G = "ovar"
d(G, "opts-then-var-target", 'rm $OPTS "$X"', "expansion")
d(G, "opts-then-bare-var-target", "rm $OPTS $X", "expansion")
d(G, "braces-opts-var-target", 'rm ${OPTS} "$X"', "expansion")
d(G, "flags-and-f", 'rm -f $FLAGS "$X"', "expansion")
d(G, "opts-then-tilde", "rm $OPTS ~/x", "tilde")
d(G, "flags-then-protected", "rm $FLAGS /tmp/ok /usr", "protected-path")
d(G, "flags-then-root", "rm $FLAGS /", "protected-path")
d(G, "flags-then-star-in-home", "rm $FLAGS *", "protected-glob", cwd="home")
d(G, "flags-unknown-cwd-dot", "rm $FLAGS .", "unknown-cwd", cwd="none")
d(G, "opts-sudo", 'sudo rm $OPTS "$X"', "expansion")
d(G, "opts-in-bash-c", "bash -c 'rm $OPTS \"$X\"'", "expansion")
d(G, "opts-cmdsubst", 'rm $(echo -rf) "$X"', "expansion")
d(G, "recursive-after-dashdash-var", 'rm -r -- $X', "expansion")
d(G, "opts-xargs", 'xargs rm $OPTS "$X"', "expansion")
a(G, "flags-safe-literal", "rm $FLAGS /tmp/x")
a(G, "flags-relative-name", "rm $FLAGS build")
a(G, "flags-two-literals", "rm $FLAGS /tmp/x ./dist")
a(G, "braces-flags-safe-literal", "rm ${FLAGS} /tmp/x")
a(G, "opts-cmdsubst-safe-literal", "rm $(echo -rf) /tmp/x")
a(G, "quoted-opts-safe-name", 'rm "$OPTS" x')
a(G, "quoted-opts-var-target-not-recursive", 'rm "$OPTS" "$X"')
a(G, "dashdash-var-target-not-option", "rm -- $X")
a(G, "dashdash-quoted-var-target", 'rm -- "$X"')
a(G, "dashdash-then-flag-like-target", "rm -- $X -rf")
a(G, "plain-f-var", 'rm -f "$X"')
a(G, "opts-safe-literal-mktemp", 'd=$(mktemp -d); rm $OPTS "$d"')
a(G, "opts-safe-literal-assign", 'D=/tmp/x; rm $OPTS "$D"')
a(G, "rmdir-opts", 'rmdir $OPTS "$X"')
a(G, "echo-text-opts", "echo rm $OPTS $X")

# ===========================================================================
# Revision 2 (spec section "修订 2"): cases follow the spec items one by one.
# Group prefix per spec section: r2g (1 globs) r2c (2 cwd) r2v (3 variable
# exceptions) r2n (4 forms and nesting) r2p (5 parsing) r2t (7 tests) r2h (8
# aliases); section 6 (log) and the exception paths of 5.3 / 7.2 are separate
# checks further down. Every case has the tag r2:<item>.
# ===========================================================================
R2_SECTION_GROUP = {"1": "r2g", "2": "r2c", "3": "r2v", "4": "r2n", "5": "r2p", "6": "r2l", "7": "r2t", "8": "r2h"}
R2_COUNT = {}        # item -> [allow cases, deny cases]
R2_ITEMS = ["1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "3.1", "3.2", "3.3", "3.4", "3.5",
            "4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.8", "5.1", "5.2", "5.3", "5.4",
            "6.1", "6.2", "7.1", "7.2", "7.3", "8.1", "8.2"]
SPECIAL_ITEMS = ("5.3", "6.1", "6.2", "7.1", "7.2")   # implemented as separate checks (not table rows)


def _r2(item, slug, cmd, expect, rule, cwd, target, only, needs):
    group = R2_SECTION_GROUP[item.split(".")[0]]
    c = R2_COUNT.setdefault(item, [0, 0])
    c[0 if expect == "allow" else 1] += 1
    _add(group, "%s-%s" % (item.replace(".", "_"), slug), cmd, expect, rule, cwd, target,
         ("r2", "r2:" + item), only, needs)


def rd(item, slug, cmd, rule, cwd="work", target=None, only=None, needs=None):
    _r2(item, slug, cmd, "deny", rule, cwd, target, only, needs)


def ra(item, slug, cmd, cwd="work", only=None, needs=None):
    _r2(item, slug, cmd, "allow", None, cwd, None, only, needs)


def rds(item, rule, rows, cwd="work", **kw):
    """rows: (slug, cmd) or (slug, cmd, cwd)."""
    for row in rows:
        rd(item, row[0], row[1], rule, cwd=(row[2] if len(row) > 2 else cwd), **kw)


def ras(item, rows, cwd="work", **kw):
    for row in rows:
        ra(item, row[0], row[1], cwd=(row[2] if len(row) > 2 else cwd), **kw)


# ---------------------------------------------------------------------------
# section 1: globs
# ---------------------------------------------------------------------------
# 1.1 a pattern that could match a protected path, compared level by level
rds("1.1", "protected-glob", [
    ("parent-name2-star", "rm -rf {REALHOME_PARENT}/{RN2}*"),                  # /Users/<na>*
    ("parent-name3-star", "rm -rf {REALHOME_PARENT}/{RN3}*"),                  # /Users/<nam>*
    ("parent-last-question", "rm -rf {REALHOME_PARENT}/{RN_Q}"),               # /Users/<nam>?
    ("parent-pstar", "rm -rf {REALHOME_PARENT}/{RN_PSTAR}"),                   # /Users/<nam>*
    ("parent-pstar-slash", "rm -rf {REALHOME_PARENT}/{RN_PSTAR}/"),            # /Users/<nam>*/
    ("parent-bracket-second", "rm -rf {REALHOME_PARENT}/{RN_BR}"),             # /Users/<n>[a]<me>
    ("parent-bracket-last", "rm -rf {REALHOME_PARENT}/{RN_LASTBR}"),           # /Users/<nam>[e]
    ("parent-prefix-and-suffix", "rm -rf {REALHOME_PARENT}/{RN_MID2}"),        # /Users/<na>*<me>
    ("level0-glob-then-home", "rm -rf {RL0}"),                                 # /Us*/<name>
    ("level0-glob-both-ends", "rm -rf {RL0B}"),                                # /Us*rs/<name>
    ("home-dotdot-then-glob", "rm -rf {REALHOME}/../{RN2}*"),                  # /Users/<name>/../<na>*
    ("cwd-parent-relative-glob", "rm -rf {RN2}*", "{REALHOME_PARENT}"),        # cwd /Users, <na>*
    ("cd-parent-and-glob", "cd {REALHOME_PARENT} && rm -rf {RN2}*"),
    ("sudo-glob", "sudo rm -rf {REALHOME_PARENT}/{RN2}*"),
    ("system-U-star", "rm -rf /U*"),
    ("system-us-star", "rm -rf /us*"),
    ("system-pri-star", "rm -rf /pri*"),
    ("system-bin-question", "rm -rf /bi?"),
    ("system-var-star", "rm -rf /v*"),
    ("private-equivalent-tmp", "rm -rf /privat?/tmp"),                         # /private/tmp is /tmp
    ("private-equivalent-t-star", "rm -rf /private/t*"),
    ("subprocess-home-prefix", "rm -rf {BASE}/ho*"),                           # HOME env is {BASE}/home
])
ras("1.1", [
    ("tmp-abc-star", "rm -rf /tmp/abc*"),
    ("tmp-build-dash-star", "rm -rf /tmp/build-*"),
    ("other-user-prefix", "rm -rf /Users/zz-nobody-zz*"),
    ("opt-foo-star", "rm -rf /opt/foo*"),
    ("work-build-star", "rm -rf {WORK}/build*"),
    ("home-proj-star", "rm -rf {REALHOME}/proj*"),
    ("mid-glob-below-tmp", "rm -rf /tmp/x*/sub"),
    ("usr-local-lib-archives", "rm -rf /usr/local/lib/*.a"),
])
# 1.2 wildcard-only level directly below a protected directory
rds("1.2", "protected-glob", [
    ("tmp-star-dot-star", "rm -rf /tmp/*.*"),
    ("usr-question-star", "rm -rf /usr/?*"),
    ("opt-dot-question-star", "rm -rf /opt/.??*"),
    ("var-bracket-star", "rm -rf /var/[a-z]*"),
    ("etc-star-dot-star", "rm -rf /etc/*.*"),
    ("subprocess-home-star-dot-star", "rm -rf {HOME}/*.*"),
    ("subprocess-home-question-star", "rm -rf {HOME}/?*"),
    ("cwd-home-star-dot-star", "rm -rf *.*", "home"),
])
ras("1.2", [
    ("tmp-star-bak", "rm -rf /tmp/*.bak"),
    ("tmp-star-log", "rm -rf /tmp/*.log"),
    ("etc-star-conf", "rm -rf /etc/*.conf"),
    ("realhome-star-log", "rm -rf {REALHOME}/*.log"),
    ("subprocess-home-star-log", "rm -rf {HOME}/*.log"),
    ("subprocess-home-dot-cache-star", "rm -rf {HOME}/.cache*"),
    ("var-log-star", "rm -rf /var/log/*"),
    ("cwd-home-star-tmp", "rm -rf *.tmp", "home"),
])
# 1.3 brace lists and sequences, 256 results at most
rds("1.3", "protected-path", [
    ("list-includes-home", "rm -rf {/tmp/x,{REALHOME}}"),
    ("sequence-last-char-home", "rm -rf {REALHOME_PARENT}/{RN_SEQ}"),          # /Users/<nam>{e..e}
    ("sequence-two-letters-home", "rm -rf {REALHOME_PARENT}/{RN_SEQ2}"),       # /Users/<nam>{e..f}
    ("sequence-users", "rm -rf /User{r..s}"),
    ("sequence-first-char-usr", "rm -rf /{u..v}sr"),
    ("list-of-256-still-judged", "rm -rf {/tmp/x,{REALHOME}}{,}{,}{,}{,}{,}{,}{,}"),
])
rds("1.3", "unparsable", [
    ("list-over-256-home-last", "rm -rf {/tmp/x,{REALHOME}}{,}{,}{,}{,}{,}{,}{,}{,}"),
    ("list-over-256-all-literal", "rm -rf /tmp/{a,b}{c,d}{e,f}{g,h}{i,j}{k,l}{m,n}{o,p}{q,r}"),
    ("sequence-over-256", "rm -rf /tmp/x{1..257}"),
])
ras("1.3", [
    ("sequence-numbers", "rm -rf /tmp/x{1..3}"),
    ("sequence-letters", "rm -rf /tmp/{a..c}"),
    ("sequence-with-suffix", "rm -rf /tmp/f{1..3}.log"),
    ("list-exactly-256", "rm -rf /tmp/{a,b}{c,d}{e,f}{g,h}{i,j}{k,l}{m,n}{o,p}"),
    ("sequence-exactly-256", "rm -rf /tmp/x{1..256}"),
    ("braces-without-comma-are-literal", "rm -rf /tmp/{abc}"),
])
# 1.4 macOS: prefix folding ignores case
rds("1.4", "protected-path", [
    ("data-volume-lowercase-home", "rm -rf /system/volumes/data{REALHOME}"),
    ("data-volume-uppercase-home", "rm -rf /SYSTEM/VOLUMES/DATA{REALHOME}"),
    ("data-volume-lowercase-users-dir", "rm -rf /system/volumes/data/users/{RN}"),
    ("private-tmp-uppercase", "rm -rf /PRIVATE/TMP"),
    ("private-var-mixed", "rm -rf /Private/Var"),
    ("private-etc-last-uppercase", "rm -rf /private/ETC"),
], only="darwin")
ras("1.4", [
    ("private-tmp-uppercase-sub", "rm -rf /PRIVATE/TMP/abc"),
    ("data-volume-lowercase-tmp-sub", "rm -rf /system/volumes/data/tmp/abc"),
    ("private-var-mixed-tmp-sub", "rm -rf /Private/Var/tmp/abc"),
])

# ---------------------------------------------------------------------------
# section 2: working directory
# ---------------------------------------------------------------------------
# 2.1 cd inside a subshell, substitution, process substitution or a non-last pipe segment stays inside
rds("2.1", "protected-glob", [
    ("subshell-then-star", "(cd /tmp/x); rm -rf *"),
    ("subshell-make-then-dot-star", "(cd /tmp/x && make clean); rm -rf ./*"),
    ("subshell-make-then-star", "(cd /tmp/x && make); rm -rf *"),
    ("cmdsubst-pwd-then-star", "X=$(cd /tmp/x; pwd); rm -rf *"),
    ("cmdsubst-bare-then-star", "X=$(cd /tmp/a); rm -rf *"),
    ("cmdsubst-in-echo-then-star", "echo $(cd /tmp/x && pwd) && rm -rf *"),
    ("backtick-then-star", "echo `cd /tmp/x`; rm -rf *"),
    ("pipe-non-last-then-star", "cd /tmp/x | cat; rm -rf *"),
    ("pipe-non-last-brace-then-dot-star", "{ cd /tmp/x; } | cat; rm -rf ./*"),
], cwd="home")
rds("2.1", "protected-path", [
    ("procsubst-then-dot", "cat <(cd /tmp/x); rm -rf ."),
    ("subshell-then-dot", "(cd /tmp/x); rm -rf ."),
], cwd="home")
ras("2.1", [
    ("star-inside-subshell", "(cd /tmp/x && rm -rf *)"),
    ("dot-star-inside-subshell-chain", "(cd /tmp/x && make && rm -rf ./*)"),
    ("named-after-subshell", "(cd /tmp/x); rm -rf build"),
    ("named-after-cmdsubst", "X=$(cd /tmp/x && pwd); rm -rf ./build ./dist"),
    ("named-after-non-last-pipe", "cd /tmp/x | cat; rm -rf build"),
    ("cd-and-rm-both-inside-cmdsubst", "echo $(cd /tmp/x && rm -rf *)"),
], cwd="home")
# 2.2 (revision 2 wording; revision 3 item 2.3 replaces the unknown-cwd results below with the possible-cwd union)
# revision 3 item 2.3: after ";" / newline / "||" / a branch the cwd is {old cwd} + {new cwd}; the old one (home) is protected,
# so the rule is the one the home possibility hits (revision 2 reported unknown-cwd for all of these)
for _slug, _cmd, _rule in [
    ("semicolon-star", "cd /tmp/does-not-exist; rm -rf *", "protected-glob"),
    ("semicolon-dot-star", "cd /tmp/x; rm -rf ./*", "protected-glob"),
    ("semicolon-dotdot", "cd /tmp/x; rm -rf ..", "protected-path"),
    ("newline-star", "cd /tmp/x\nrm -rf *", "protected-glob"),
    ("or-true-dot-star", "cd /tmp/x || true; rm -rf ./*", "protected-glob"),
    ("or-true-dot", "cd /tmp/x || true; rm -rf .", "protected-path"),
    ("or-then-rm", "cd /tmp/x || rm -rf *", "protected-glob"),
    ("if-body-then-star", "if [ -d /tmp/x ]; then cd /tmp/x; fi; rm -rf *", "protected-glob"),
    ("case-body-then-star", "case x in a) cd /tmp/x;; esac; rm -rf *", "protected-glob"),
    ("loop-body-then-star", "for d in a b; do cd /tmp/x; done; rm -rf *", "protected-glob"),
]:
    rd("2.2", _slug, _cmd, _rule, cwd="home")
rds("2.2", "protected-glob", [
    ("noarg-and-star", "cd && rm -rf *"),
    ("tilde-and-chain-star", "cd ~ && cd .. && rm -rf *"),
    ("tilde-slash-and-star", "cd ~/ && rm -rf *"),
])
rds("2.2", "protected-path", [
    ("tilde-sub-and-dotdot", "cd ~/proj && rm -rf .."),
    ("tilde-and-chain-dotdot", "cd ~ && cd proj && rm -rf .."),
])
ras("2.2", [
    ("and-chain-star", "cd /tmp/x && cd sub && rm -rf *"),
    ("tilde-sub-and-star", "cd ~/proj && rm -rf *"),
    ("tilde-then-sub-and-star", "cd ~ && cd proj && rm -rf *"),
    ("semicolon-then-named", "cd /tmp/x; rm -rf build"),
    ("or-exit-then-named", "cd /tmp/x || exit 1; rm -rf dist"),
    ("if-body-and-chain-star", "if true; then cd /tmp/x && rm -rf *; fi"),
    ("pushd-and-dot-star", "pushd /tmp/x >/dev/null && rm -rf ./*"),
], cwd="home")
# 2.3 find: default start point, option skipping, relative start points
rds("2.3", "expansion", [
    ("dashdash-var", 'find -- "$X" -delete'),
    ("L-var", 'find -L "$X" -delete'),
    ("P-var-exec-rm", 'find -P "$X" -exec rm {} +'),
    ("D-value-var", 'find -D tree "$X" -delete'),
    ("O3-var", 'find -O3 "$X" -delete'),
])
rds("2.3", "tilde", [
    ("dashdash-tilde", "find -- ~ -delete"),
    ("H-tilde", "find -H ~ -name x -delete"),
])
rds("2.3", "protected-path", [
    ("no-start-delete-in-home", "find -delete", "home"),
    ("no-start-name-delete-in-home", "find -name '*.tmp' -delete", "home"),
    ("no-start-exec-rm-in-home", "find -exec rm {} +", "home"),
    ("no-start-after-cd-home", "cd ~ && find -delete"),
    ("D-value-then-realhome", "find -D tree {REALHOME} -delete"),
    ("dotdot-from-work", "find .. -delete"),
])
rds("2.3", "unknown-cwd", [
    ("no-start-delete-no-cwd", "find -delete", "none"),
    ("dot-delete-no-cwd", "find . -delete", "none"),
    ("dotdot-delete-no-cwd", "find .. -name x -delete", "none"),
    ("dot-delete-after-cd-var", 'cd "$X" && find . -delete'),
])
ras("2.3", [
    ("no-start-delete-in-work", "find -name '*.pyc' -delete"),
    ("no-start-delete-in-subdir", "find -delete", "{WORK}/sub"),
    ("dashdash-literal", "find -- build -delete"),
    ("H-literal", "find -H dist -name x -delete"),
    ("D-value-literal", "find -D tree build -delete"),
    ("O2-literal-tmp", "find -O2 /tmp/abc -delete"),
    ("dot-delete-in-work", "find . -delete"),
    ("no-start-without-delete-in-home", "find -type f -name '*.o'", "home"),
    ("dot-without-delete-no-cwd", "find . -name x", "none"),
])

# ---------------------------------------------------------------------------
# section 3: variable exceptions
# ---------------------------------------------------------------------------
# 3.1 only assignments that certainly ran before the rm count
# revision 3 items 1.2 / 1.3: a possibly-not-run assignment is unioned into the old set. The old set is the earlier certain
# value, or {empty} when the name was never assigned before; a quoted empty "$X" is harmless, "$X"/* becomes /*
_G3 = ("expansion", "protected-glob")   # either report is acceptable: the name may be read as unknown or as empty
for _slug, _cmd, _rule in [
    ("or-right-mktemp-over-unknown", 'D="$APP_HOME"; [ -d "$D" ] || D=$(mktemp -d); rm -rf "$D"', "expansion"),
    ("and-right-literal-over-unknown", 'D="$HOME"; test -n "$CI" && D=/tmp/ci; rm -rf "$D"', "expansion"),
    ("or-right-literal-home", '[ -n "$HOME" ] || HOME=/tmp/x; rm -rf "$HOME"', "expansion"),  # first-round P1 repro: must stay denied (see the report on HOME)
    ("and-right-glob", '[ -n "$CI" ] && X=/tmp/a; rm -rf "$X"/*', _G3),
    ("and-right-glob-quoted-slash", '[ -d /nope ] && D=/tmp/a; rm -rf "$D/"*', _G3),
    ("or-right-mktemp-plain", '[ -d /tmp/x ] || d=$(mktemp -d); rm -rf "$d"', None),  # revision 3: {empty, mktemp}, quoted bare target is harmless (was expansion)
    ("and-right-rm-after-semicolon", 'true && D=/tmp/x; rm -rf "$D"', None),  # revision 3: {empty, /tmp/x} (was expansion)
    ("if-false-keeps-old-value", 'X=$HOME; if false; then X=/tmp/a; fi; rm -rf "$X"', "expansion"),
]:
    if _rule is None:
        ra("3.1", _slug, _cmd)
    else:
        rd("3.1", _slug, _cmd, _rule)
ras("3.1", [
    ("and-chain-both-sides", 'true && D=/tmp/x && rm -rf "$D"'),
    ("and-chain-mktemp", 'echo start && d=$(mktemp -d) && rm -rf "$d"'),
    ("and-chain-glob", 'test -d /tmp && D=/tmp/x && rm -rf "$D"/*'),
    ("semicolons-between", 'D=/tmp/x; echo hi; rm -rf "$D"'),
    ("newlines-between", 'D=/tmp/x\necho hi\nrm -rf "$D"'),
    ("left-of-or", 'd=$(mktemp -d) || exit 1; rm -rf "$d"'),
])
# 3.2 assignments inside if / case / loop bodies are valid only inside that body
# revision 3 item 1.3: a body assignment is unioned into the old set after the body ends. Every possible value here is harmless
# for a bare quoted target, so those rows are allow now (revision 2 reported expansion); the glob / subpath rows stay denied
for _slug, _cmd, _rule in [
    ("case-both-branches-then-outside", 'case "$1" in a) D=/tmp/a;; *) D=/tmp/b;; esac; rm -rf "$D"', None),
    ("if-else-then-outside", 'if [ -n "$Q" ]; then D=/tmp/a; else D=/tmp/b; fi; rm -rf "$D"', None),
    ("if-then-outside-glob", 'if [ -d /tmp/x ]; then D=/tmp/x; fi; rm -rf "$D/"*', _G3),
    ("old-value-voided-by-body", 'D=/tmp/x; if true; then D=/tmp/y; fi; rm -rf "$D"', None),  # {/tmp/x, /tmp/y}: both harmless
    ("for-body-then-outside", 'for f in a; do D=/tmp/x; done; rm -rf "$D"', None),
    ("while-body-then-outside", 'while true; do D=/tmp/x; break; done; rm -rf "$D"', None),
    ("mktemp-in-if-then-outside", 'if true; then d=$(mktemp -d); fi; rm -rf "$d"', None),
]:
    if _rule is None:
        ra("3.2", _slug, _cmd)
    else:
        rd("3.2", _slug, _cmd, _rule)
ras("3.2", [
    ("case-body-same-branch", 'case "$1" in a) D=/tmp/a; rm -rf "$D";; esac'),
    ("if-body-same-body", 'if [ -n "$Q" ]; then D=/tmp/a; rm -rf "$D"; fi'),
    ("else-body-same-body", 'if [ -n "$Q" ]; then :; else D=/tmp/b; rm -rf "$D"; fi'),
    ("for-body-same-body", 'for f in a b; do D=/tmp/x; rm -rf "$D"; done'),
    ("mktemp-in-body-same-body", 'if true; then d=$(mktemp -d); rm -rf "$d"; fi'),
])
# 3.3 subshell, substitution, process substitution, pipeline segments do not change the outside
rds("3.3", "expansion", [
    ("subshell-literal-then-outside", '(D=/tmp/x); rm -rf "$D"/*'),
    ("subshell-over-unknown", 'X=$HOME; (X=/tmp/safe); rm -rf "$X"'),
    ("spaced-subshell-glob", '( X=/tmp/a ); rm -rf "$X"/*'),
    ("cmdsubst-over-unknown", 'X=$HOME; : $(X=/tmp/safe); rm -rf "$X"'),
    ("cmdsubst-in-echo", 'echo $(X=/tmp/a); rm -rf "$X"/*'),
    ("pipe-segment-over-unknown", 'X=$HOME; X=/tmp/safe | cat; rm -rf "$X"'),
    ("pipe-segment-glob", 'X=/tmp/a | cat; rm -rf "$X"/*'),
    ("procsubst-literal", 'cat <(D=/tmp/x); rm -rf "$D"'),
])
ras("3.3", [
    ("subshell-keeps-outer-value", 'D=/tmp/x; (D=$HOME); rm -rf "$D"'),
    ("cmdsubst-keeps-outer-value", 'D=/tmp/x; X=$(D=/etc; echo hi); rm -rf "$D"'),
    ("pipe-segment-keeps-outer-value", 'D=/tmp/x; D=$HOME | cat; rm -rf "$D"'),
    ("procsubst-keeps-outer-value", 'D=/tmp/x; cat <(D=$HOME); rm -rf "$D"'),
    ("subshell-keeps-outer-mktemp", 'd=$(mktemp -d); (d=/); rm -rf "$d"'),
])
# 3.4 builtins that set a name make it unknown; source / eval / function calls void everything
rds("3.4", "expansion", [
    ("printf-v", 'X=/tmp/x; printf -v X %s "$HOME"; rm -rf "$X"'),
    ("printf-v-slash", 'X=/tmp/a; printf -v X /; rm -rf "$X"'),
    ("printf-v-quoted-format", "D=/tmp/x; printf -v D '%s' \"$HOME\"; rm -rf \"$D\""),
    ("read", 'D=/tmp/x; read -r D < /tmp/f; rm -rf "$D"'),
    ("read-two-names", 'D=/tmp/x; read A D < /tmp/f; rm -rf "$D"'),
    ("declare-n", 'declare -n X=HOME; rm -rf "$X"'),
    ("declare-n-over-literal", 'D=/tmp/x; declare -n D=HOME; rm -rf "$D"'),
    ("local-n", 'D=/tmp/x; local -n D=HOME; rm -rf "$D"'),
    ("typeset-n", 'D=/tmp/x; typeset -n D=HOME; rm -rf "$D"'),
    ("export-n", 'D=/tmp/x; export -n D=HOME; rm -rf "$D"'),
    ("mapfile", 'D=/tmp/x; mapfile -t D < /tmp/f; rm -rf "$D"'),
    ("readarray", 'D=/tmp/x; readarray D < /tmp/f; rm -rf "$D"'),
    ("getopts", 'D=/tmp/x; getopts "ab" D; rm -rf "$D"'),
    ("for-variable", 'D=/tmp/x; for D in a b; do :; done; rm -rf "$D"'),
    ("select-variable", 'D=/tmp/x; select D in a b; do break; done; rm -rf "$D"'),
    ("source", 'D=/tmp/x; source ./env.sh; rm -rf "$D"'),
    ("dot-source", 'D=/tmp/x; . ./env.sh; rm -rf "$D"'),
    ("eval", 'D=/tmp/x; eval "$CMD"; rm -rf "$D"'),
    ("function-call", 'f() { :; }; D=/tmp/x; f; rm -rf "$D"'),
    ("source-voids-mktemp", 'd=$(mktemp -d); source ./env.sh; rm -rf "$d"'),
    ("function-call-voids-mktemp", 'g() { :; }; d=$(mktemp -d); g; rm -rf "$d"'),
])
ras("3.4", [
    ("printf-v-other-name", 'D=/tmp/x; printf -v E %s hi; rm -rf "$D"'),
    ("read-other-name", 'D=/tmp/x; read E < /tmp/f; rm -rf "$D"'),
    ("declare-n-other-name", 'D=/tmp/x; declare -n E=HOME; rm -rf "$D"'),
    ("getopts-other-name", 'D=/tmp/x; getopts "ab" E; rm -rf "$D"'),
    ("for-other-variable", 'D=/tmp/x; for f in a b; do :; done; rm -rf "$D"'),
    ("function-defined-not-called", 'f() { echo hi; }; D=/tmp/x; rm -rf "$D"'),
    ("assign-again-after-source", 'D=/tmp/x; source ./env.sh; D=/tmp/y; rm -rf "$D"'),
    ("assign-after-eval", 'eval "$CMD"; D=/tmp/x; rm -rf "$D"'),
    ("mktemp-after-function-call", 'f() { :; }; f; d=$(mktemp -d); rm -rf "$d"'),
])
# 3.5 trap strings use the record at the end of the command
rds("3.5", "expansion", [
    ("mktemp-then-reassigned-unknown", "d=$(mktemp -d); trap 'rm -rf \"$d\"' EXIT; d=$HOME"),
    ("literal-then-voided-by-source", "D=/tmp/x; trap 'rm -rf \"$D\"' EXIT; source ./env.sh"),
    ("literal-then-printf-v", "D=/tmp/x; trap 'rm -rf \"$D\"' EXIT; printf -v D %s \"$HOME\""),
])
ra("3.5", "literal-then-emptied", "D=/tmp/x; trap 'rm -rf \"$D\"' EXIT; D=")  # revision 3 item 1.5: the final value is {empty}, a quoted empty target is harmless (was expansion)
rds("3.5", "protected-path", [
    ("literal-then-system-dir", "D=/tmp/x; trap 'rm -rf \"$D\"' EXIT; D=/usr"),
    ("mktemp-then-slash", "d=$(mktemp -d); trap 'rm -rf \"$d\"' EXIT; d=/"),
])
ras("3.5", [
    ("assignment-after-trap", "trap 'rm -rf \"$d\"' EXIT; d=$(mktemp -d)"),
    ("literal-reassigned-safe", "D=/tmp/x; trap 'rm -rf \"$D\"' EXIT; D=/tmp/y"),
    ("subshell-assignment-ignored", "D=/tmp/x; trap 'rm -rf \"$D\"' EXIT; (D=/usr)"),
    ("mktemp-multi-signal", "d=$(mktemp -d); trap 'rm -rf \"$d\"' EXIT INT TERM; cp a \"$d/\""),
])

# ---------------------------------------------------------------------------
# section 4: calling forms and nested text
# ---------------------------------------------------------------------------
# 4.1 function definitions and more wrappers
rds("4.1", "protected-path", [
    ("function-keyword-home", "function f { rm -rf {REALHOME}; }; f"),
    ("function-keyword-named-home", "function cleanup { rm -rf {REALHOME}; }; cleanup"),
    ("flock-wait-option-usr", "flock -w 5 /tmp/l rm -rf /usr"),
])
rds("4.1", "tilde", [
    ("function-keyword-tilde", "function f { rm -rf ~; }"),
    ("coproc-tilde", "coproc rm -rf ~"),
    ("nocorrect-tilde", "nocorrect rm -rf ~"),
    ("flock-nonblock-tilde", "flock -n /tmp/l rm -rf ~"),
    ("stdbuf-tilde", "stdbuf -o0 -e0 rm -rf ~"),
    ("ionice-class-value-tilde", "ionice -c 2 -n 7 rm -rf ~"),
    ("watch-quoted-tilde", "watch 'rm -rf ~'"),
])
rds("4.1", "expansion", [
    ("function-keyword-var", 'function f { rm -rf "$X"; }; f'),
    ("function-keyword-parens-var", 'function f() { rm -rf "$X"; }'),
    ("function-keyword-newline-brace", 'function f\n{\n  rm -rf "$X"\n}\nf'),
    ("coproc-named-compound", 'coproc BG { rm -rf "$X"; }'),
    ("noglob-var", 'noglob rm -rf "$X"'),
    ("builtin-command-var", 'builtin command rm -rf "$X"'),
    ("flock-var", 'flock /tmp/l rm -rf "$X"'),
    ("chronic-var", 'chronic rm -rf "$X"'),
    ("setsid-var", 'setsid rm -rf "$X"'),
    ("setsid-fork-var", 'setsid -f rm -rf "$X"'),
    ("stdbuf-var", 'stdbuf -oL rm -rf "$X"'),
    ("unbuffer-var", 'unbuffer rm -rf "$X"'),
    ("ionice-var", 'ionice -c3 rm -rf "$X"'),
    ("watch-options-var", 'watch -n 5 rm -rf "$X"'),
])
ras("4.1", [
    ("function-keyword-safe-body", "function f { echo hi; }; f"),
    ("function-keyword-literal-rm", "function f { rm -rf /tmp/abc; }; f"),
    ("function-keyword-non-recursive", 'function f() { rm -f "$X"; }'),
    ("coproc-benign", "coproc echo hi"),
    ("noglob-literal", "noglob rm -rf /tmp/abc"),
    ("flock-literal", "flock /tmp/l rm -rf /tmp/abc"),
    ("ionice-literal", "ionice -c3 rm -rf /tmp/abc"),
    ("setsid-fork-literal", "setsid -f rm -rf /tmp/abc"),
    ("watch-benign", "watch -n 5 ls /tmp"),
    ("stdbuf-benign", "stdbuf -oL echo hi"),
])
# 4.2 the command name itself is an expansion
rds("4.2", "expansion", [
    ("leading-var-then-rm", '$SUDO rm -rf "$HOME"'),
    ("var-as-command-with-recursive-option", '$RM -rf "$X"'),
    ("default-form-as-command-var-target", '${RM:-rm} -rf "$X"'),
    ("shell-var-dash-c", "$SHELL -c 'rm -rf \"$X\"'"),
    ("quoted-var-as-command", '"$X" -rf "$Y"'),
    ("leading-var-then-wrapper", '$SUDO nice rm -rf "$X"'),
])
rds("4.2", "protected-path", [
    ("cmdsubst-as-command-recursive-option", "$(which rm) -rf {REALHOME}"),
    ("shell-braces-dash-c", "${SHELL} -c 'rm -rf /usr'"),
    ("var-as-command-system-dir", "$RM -rf /usr"),
])
rds("4.2", "tilde", [
    ("default-form-as-command", "${RM:-rm} -rf ~"),
    ("shell-quoted-dash-c", "\"$SHELL\" -c 'rm -rf ~'"),
    ("shell-login-dash-c", "$SHELL -lc 'rm -rf ~/x'"),
])
ras("4.2", [
    ("leading-var-then-safe-rm", "$SUDO rm -rf /tmp/abc"),
    ("leading-var-then-non-recursive-rm", '$SUDO rm "$f"'),
    ("var-command-no-recursive-option", '$EDITOR "$FILE"'),
    ("var-command-plain-options", "$CC -o out main.c"),
    ("var-command-recursive-option-safe-target", "$CMD -rf /tmp/abc"),
    ("shell-var-benign-script", "$SHELL -c 'echo hi'"),
    ("shell-var-safe-rm", "\"$SHELL\" -c 'rm -rf /tmp/abc'"),
])
# 4.3 substitutions in an unquoted heredoc body are executed by the shell, whatever the command
rds("4.3", "expansion", [
    ("cat-backtick", "cat > a.md <<EOF\nstep: `rm -rf $HOME/x`\nEOF"),
    ("tee-cmdsubst-var", 'tee a.md <<EOF\ndone: $(rm -rf "$X")\nEOF'),
    ("cat-stdout-backtick-var", 'cat <<EOF\n`rm -rf "$X"`\nEOF'),
    ("cat-second-line", 'cat > a.md <<EOF\nline one\nrun: $(rm -rf "$D")\nEOF'),
])
rds("4.3", "tilde", [
    ("cat-cmdsubst-tilde", "cat > a.md <<EOF\n$(rm -rf ~)\nEOF"),
    ("dash-heredoc-cmdsubst-tilde", "cat <<-EOF\n\t$(rm -rf ~)\nEOF"),
])
rds("4.3", "protected-path", [
    ("python-cmdsubst-system-dir", 'python3 - <<EOF\nx = "$(rm -rf /usr)"\nEOF'),
    ("cat-backtick-realhome", "cat <<EOF\n`rm -rf {REALHOME}`\nEOF"),
])
ras("4.3", [
    ("quoted-delimiter-cmdsubst", "cat > a.md <<'EOF'\n$(rm -rf \"$X\")\nEOF"),
    ("double-quoted-delimiter-backtick", 'cat > a.md <<"EOF"\n`rm -rf ~`\nEOF'),
    ("benign-substitutions", "cat > a.md <<EOF\nuse: $(date) and `hostname`\nEOF"),
    ("plain-text-with-variable", 'cat > a.md <<EOF\nrm -rf "$HOME" is dangerous\nEOF'),
    ("literal-safe-substitution", "cat > a.md <<EOF\n$(rm -rf /tmp/abc)\nEOF"),
    ("non-recursive-substitution", 'cat > a.md <<EOF\n$(rm -f "$X")\nEOF'),
])
# 4.4 here-strings and pipelines that end in a shell
rds("4.4", "tilde", [
    ("herestring-bash", "bash <<< 'rm -rf ~'"),
    ("herestring-ssh", "ssh host <<< 'rm -rf ~/x'"),
    ("echo-pipe-bash", "echo 'rm -rf ~' | bash"),
    ("echo-pipe-ssh-sh", "echo 'rm -rf ~/x' | ssh host sh"),
    ("heredoc-through-tee-to-bash", "cat <<'EOF' | tee log | bash\nrm -rf ~\nEOF"),
])
rds("4.4", "expansion", [
    ("herestring-dq-var", 'bash <<< "rm -rf $HOME"'),
    ("herestring-sh", "sh <<< 'rm -rf \"$X\"'"),
    ("herestring-ssh-bash", "ssh host bash <<< 'rm -rf $HOME'"),
    ("printf-pipe-sh", "printf '%s\\n' 'rm -rf \"$X\"' | sh"),
    ("heredoc-to-ssh-bash", "cat <<'EOF' | ssh host bash\nrm -rf \"$X\"\nEOF"),
    ("echo-pipe-bash-dollar-home", "echo 'rm -rf $HOME' | bash"),
])
rds("4.4", "protected-path", [
    ("herestring-zsh", "zsh <<< 'rm -rf /usr'"),
    ("echo-through-tee-to-bash", "echo 'rm -rf /usr' | tee log | bash"),
])
ras("4.4", [
    ("herestring-bash-benign", "bash <<< 'echo hi'"),
    ("herestring-bash-literal-rm", "bash <<< 'rm -rf /tmp/abc'"),
    ("echo-pipe-cat", "echo 'rm -rf ~' | cat"),
    ("echo-pipe-tee", "echo 'rm -rf \"$X\"' | tee notes.md"),
    ("echo-pipe-bash-dash-c-ignores-stdin", "echo 'rm -rf ~' | bash -c 'cat'"),
    ("echo-pipe-grep", "echo 'rm -rf ~' | grep rm"),
    ("herestring-cat", "cat <<< 'rm -rf ~'"),
    ("echo-redirect", "echo 'rm -rf ~' > notes.md"),
    ("echo-pipe-ssh-remote-command", "echo 'rm -rf ~' | ssh host 'cat > notes.md'"),
])
# 4.5 ssh: options after the host, --, multi-word remote command
rds("4.5", "tilde", [
    ("option-after-host", "ssh host -t 'rm -rf ~'"),
    ("dashdash-quoted-tilde", "ssh host -- rm -rf '~'"),
    ("value-option-after-host", "ssh host -o StrictHostKeyChecking=no 'rm -rf ~/x'"),
])
rds("4.5", "expansion", [
    ("words-joined-single-quote-lost", "ssh host rm -rf '$HOME/x'"),
    ("dashdash-single-quoted-var", "ssh host -- rm -rf '$X'"),
    ("option-after-host-var", "ssh host -l user 'rm -rf $X'"),
])
rds("4.5", "protected-path", [
    ("double-quoted-after-options", 'ssh -p 22 host -t "rm -rf /usr"'),
    ("dashdash-generic-dir", "ssh user@host -- rm -rf /home"),
    ("words-joined-root", "ssh host rm -rf /"),
])
ras("4.5", [
    ("option-after-host-benign", "ssh host -t 'ls /tmp'"),
    ("dashdash-literal", "ssh host -- rm -rf /tmp/abc"),
    ("option-after-host-literal", "ssh host -p 22 'rm -rf /home/deploy/app'"),
    ("dashdash-non-rm", "ssh host -- ls ~"),
    ("words-joined-relative", "ssh host rm -rf build dist"),
    ("dashdash-relative", "ssh host -- rm -rf build"),
])
# 4.6 parallel with a quoted command and ::: arguments; xargs -I / -J
rds("4.6", "tilde", [
    ("parallel-arg-tilde", "parallel 'rm -rf {}' ::: ~"),
    ("xargs-I-literal-tilde", "xargs -I % rm -rf % ~"),
    ("xargs-J-literal-tilde", "xargs -J % rm -rf % ~"),
])
rds("4.6", "protected-path", [
    ("parallel-arg-system-dir", "parallel 'rm -rf {}' ::: /usr /tmp/x"),
    ("xargs-J-literal-system-dir", "xargs -J % rm -rf % /usr"),
    ("xargs-I-braces-literal-system-dir", "xargs -I{} rm -rf {} /usr"),
    ("parallel-dot-in-home", "parallel 'rm -rf {}' ::: .", "home"),
])
rds("4.6", "expansion", [
    ("parallel-dq-command-var", 'parallel "rm -rf $HOME/{}" ::: a'),
    ("parallel-arg-var", 'parallel \'rm -rf {}\' ::: "$X"'),
    ("xargs-I-literal-var", 'xargs -I{} rm -rf "$X" {}'),
])
ras("4.6", [
    ("parallel-relative-args", "parallel 'rm -rf {}' ::: a b c"),
    ("parallel-literal-prefix", "parallel 'rm -rf /tmp/{}' ::: a b"),
    ("parallel-not-rm", "parallel echo {} ::: ~"),
    ("parallel-named-dirs", "parallel 'rm -rf {}' ::: build dist"),
    ("xargs-I-replace-only", "xargs -I {} rm -rf {}"),
    ("xargs-I-literal-safe", "xargs -I % rm -rf /tmp/abc %"),
    ("xargs-J-relative-literal", "xargs -J % rm -rf % ./build"),
])
# 4.7 GNU long option abbreviations of --recursive
rds("4.7", "expansion", [
    ("r", 'rm --r "$X"'),
    ("re", 'rm --re "$X"'),
    ("rec-force", 'rm --rec -f "$X"'),
    ("grm-recur", 'grm --recur "$X"'),
    ("recurs", 'rm --recurs "$X"'),
    ("recursiv", 'rm --recursiv "$X"'),
    ("grm-rec", 'grm --rec "$X"'),
    ("after-target", 'rm "$X" --rec'),
])
rds("4.7", "tilde", [("grm-recur-tilde", "grm --recur ~"), ("rec-tilde", "rm --rec ~/x")])
rds("4.7", "protected-path", [("recurs-system-dir", "rm --recurs /usr"), ("grm-recur-home", "grm --recur -f {REALHOME}")])
ras("4.7", [
    ("force-prefix", 'rm --f "$X"'),
    ("force-full", 'rm --force "$X"'),
    ("interactive", 'rm --interactive "$X"'),
    ("verbose-prefix", 'rm --verb "$X"'),
    ("preserve-root", 'rm --preserve-root "$X"'),
    ("no-preserve-root-alone", 'rm --no-preserve-root "$X"'),
    ("one-file-system", 'rm --one-file-system "$X"'),
    ("dir-option", 'rm --dir "$X"'),
])
# 4.8 outer double quotes: literal values of the outer shell are substituted into the nested text
ras("4.8", [
    ("bash-c-dq-literal", 'D=/tmp/x; bash -c "rm -rf $D"'),
    ("ssh-dq-literal", 'D=/tmp/x; ssh h "rm -rf $D"'),
    ("sh-c-dq-literal-subpath", 'D=/tmp/x; sh -c "rm -rf $D/sub"'),
    ("eval-dq-literal", 'D=/tmp/x; eval "rm -rf $D"'),
    ("bash-c-dq-braces", 'D=/tmp/x; bash -c "rm -rf ${D}/out"'),
])
rds("4.8", "protected-path", [
    ("bash-c-dq-system-value", 'D=/usr; bash -c "rm -rf $D"'),
    ("bash-c-dq-home-value", 'D={REALHOME}; bash -c "rm -rf $D"'),
    ("ssh-dq-root-value", 'D=/; ssh h "rm -rf $D"'),
])
rds("4.8", "expansion", [
    ("bash-c-sq-not-substituted", "D=/tmp/x; bash -c 'rm -rf $D'"),
    ("ssh-sq-not-substituted", "D=/tmp/x; ssh h 'rm -rf $D'"),
    ("bash-c-dq-unknown-value", 'X=$HOME; bash -c "rm -rf $X"'),
    ("bash-c-dq-other-name", 'D=/tmp/x; bash -c "rm -rf $E"'),
    ("bash-c-dq-escaped-dollar", 'D=/tmp/x; bash -c "rm -rf \\$D"'),
])

# ---------------------------------------------------------------------------
# section 5: parsing
# ---------------------------------------------------------------------------
DEFAULT_COMMIT = ('git commit -m "$(cat <<\'EOF\'\n'
                  'fix: guard rejects rm -rf "$X"\n\n'
                  "It's the guard fix: rm -rf \"$HOME\" must not run.\n\n"
                  'Co-Authored-By: Claude <noreply@anthropic.com>\n'
                  'EOF\n'
                  ')"')
# 5.1 heredocs and comments inside $( ), <( ), >( )
ras("5.1", [
    ("claude-default-commit", DEFAULT_COMMIT),
    ("commit-apostrophe-and-rm", "git commit -m \"$(cat <<'EOF'\nfix: don't rm -rf $HOME\nEOF\n)\""),
    ("gh-pr-body", "gh pr create --title \"t\" --body \"$(cat <<'EOF'\n## Summary\n- it's fixed; rm -rf \\\"$X\\\" no longer runs\nEOF\n)\""),
    ("commit-backtick-in-body", "git commit -m \"$(cat <<'EOF'\nsubject\n\nbody with `rm -rf ~` text\nEOF\n)\""),
    ("procsubst-comment-apostrophe", "diff <(sort a # don't\n) b"),
    ("procsubst-with-heredoc", "cat <(cat <<'EOF'\nit's rm -rf \"$X\"\nEOF\n)"),
    ("unquoted-heredoc-benign-substitution", "echo \"$(cat <<EOF\nit's text $(date)\nEOF\n)\""),
])
rds("5.1", "tilde", [
    ("commit-then-rm-tilde", "git commit -m \"$(cat <<'EOF'\nit's\nEOF\n)\" && rm -rf ~"),
    ("default-commit-then-rm-tilde", DEFAULT_COMMIT + " && rm -rf ~"),
])
rds("5.1", "protected-path", [
    ("procsubst-comment-then-rm-home", "diff <(sort a # it's\n) b; rm -rf {REALHOME}"),
    ("commit-then-newline-rm-system", "git commit -m \"$(cat <<'EOF'\nit's\nEOF\n)\"\nrm -rf /usr"),
])
rds("5.1", "expansion", [
    ("echo-heredoc-then-rm-var", "echo \"$(cat <<'EOF'\nit's\nEOF\n)\"; rm -rf \"$X\""),
    ("heredoc-piped-to-bash-inside-cmdsubst", "x=$(cat <<'EOF' | bash\nrm -rf \"$X\"\nEOF\n)"),
    ("top-level-comment-with-apostrophe", "echo hi # it's a comment\nrm -rf \"$X\""),
])
# 5.2 text rule for unparsable input also looks at protected paths
rds("5.2", "unparsable", [
    ("unclosed-realhome", "rm -rf {REALHOME} 'abc"),
    ("unclosed-subprocess-home", 'rm -rf {HOME} "oops'),
    ("unclosed-root-as-word", 'rm -rf / "oops'),
    ("unclosed-system-dir", "rm -rf /Users 'x"),
    ("unclosed-etc", 'rm -r /etc "abc'),
    ("unclosed-usr-local", "rm -rf /usr/local 'x"),
])
ras("5.2", [
    ("unclosed-literal-tmp", 'rm -rf /tmp/abc /var/tmp/x "oops'),
    ("unclosed-other-user-path", 'rm -rf /Users/zz-nobody-zz/x "oops'),
    ("unclosed-non-recursive-root", 'rm -f / "oops'),
    ("unclosed-no-rm", "echo / /Users 'oops"),
    ("unclosed-relative-names", 'rm -rf build dist "oops'),
])
# 5.4 nesting limit: 8 levels are judged, level 9 is unparsable
def _wrap(n, inner, opener):
    s = inner
    for _ in range(n):
        s = opener + s + " )"
    return s


_SUB = "echo $("
_PROC = "cat <("
rds("5.4", "expansion", [
    ("cmdsubst-8-levels-judged", _wrap(8, 'rm -rf "$X"', _SUB)),
    ("procsubst-8-levels-judged", _wrap(8, 'rm -rf "$X"', _PROC)),
])
rds("5.4", "tilde", [("cmdsubst-8-levels-tilde", _wrap(8, "rm -rf ~", _SUB))])
rds("5.4", "protected-path", [("procsubst-8-levels-system-dir", _wrap(8, "rm -rf /Users", _PROC))])
rds("5.4", "unparsable", [
    ("cmdsubst-9-levels-var", _wrap(9, 'rm -rf "$X"', _SUB)),
    ("cmdsubst-9-levels-safe-literal-has-marker", _wrap(9, "rm -rf /tmp/abc", _SUB)),
    ("procsubst-9-levels-system-dir", _wrap(9, "rm -rf /Users", _PROC)),
    ("procsubst-9-levels-var", _wrap(9, 'rm -rf "$X"', _PROC)),
])
ras("5.4", [
    ("cmdsubst-8-levels-safe", _wrap(8, "rm -rf /tmp/abc", _SUB)),
    ("procsubst-8-levels-safe", _wrap(8, "rm -rf /tmp/abc", _PROC)),
    ("cmdsubst-7-levels-safe", _wrap(7, "rm -rf /tmp/abc", _SUB)),
    ("procsubst-9-levels-safe-no-marker", _wrap(9, "rm -rf /tmp/abc", _PROC)),
])

# ---------------------------------------------------------------------------
# section 7.3: Claude Code default commit form is allowed (text group of revision 2)
# ---------------------------------------------------------------------------
ras("7.3", [
    ("default-commit-with-co-author", DEFAULT_COMMIT),
    ("default-commit-apostrophe-only", "git commit -m \"$(cat <<'EOF'\nIt's a fix\n\nCo-Authored-By: Claude <noreply@anthropic.com>\nEOF\n)\""),
    ("default-commit-mentions-rm-and-home", "git commit -m \"$(cat <<'EOF'\nfix: rm -rf \\\"$HOME\\\" guard\n\nIt's the guard fix: rm -rf ~ must be refused.\nEOF\n)\""),
    ("default-commit-then-push", DEFAULT_COMMIT + " && git push origin HEAD"),
])
rds("7.3", "expansion", [("default-commit-then-rm-var", DEFAULT_COMMIT + ' && rm -rf "$X"')])
rds("7.3", "tilde", [("default-commit-newline-rm-tilde", DEFAULT_COMMIT + "\nrm -rf ~/x")])

# ---------------------------------------------------------------------------
# section 8: aliases of home and system volumes
# ---------------------------------------------------------------------------
# 8.1 the part before the last component is resolved with realpath (the last one only before / or /.)
rds("8.1", "protected-path", [
    ("bootlink-home", "rm -rf {BOOTLINK}{REALHOME}"),
    ("bootlink-home-quoted", 'rm -rf "{BOOTLINK}{REALHOME}"'),
    ("bootlink-home-sudo", "sudo rm -rf {BOOTLINK}{REALHOME}"),
    ("bootlink-users-dir", "rm -rf {BOOTLINK}{REALHOME_PARENT}"),
    ("bootlink-trailing-slash", "rm -rf {BOOTLINK}/"),
    ("bootlink-trailing-dot", "rm -rf {BOOTLINK}/."),
    ("homelink-trailing-slash", "rm -rf {HOMELINK}/"),
    ("homelink-trailing-dot", "rm -rf {HOMELINK}/."),
    ("userslink-home", "rm -rf {USERSLINK}/{RN}"),
    ("usrlink-trailing-slash", "rm -rf {USRLINK}/"),
    ("find-start-through-bootlink", "find {BOOTLINK}{REALHOME} -delete"),
])
ras("8.1", [
    ("bootlink-itself", "rm -rf {BOOTLINK}"),
    ("homelink-itself", "rm -rf {HOMELINK}"),
    ("usrlink-itself", "rm -rf {USRLINK}"),
    ("homelink-below", "rm -rf {HOMELINK}/proj/x"),
    ("usrlink-below", "rm -rf {USRLINK}/lib/foo"),
    ("userslink-other-user", "rm -rf {USERSLINK}/zz-nobody-zz"),
    ("bootlink-tmp-below", "rm -rf {BOOTLINK}/tmp/abc"),
    ("bootlink-nonexistent-below", "rm -rf {BOOTLINK}/nonexistent-zz/foo"),
])
# the real startup-volume alias under /Volumes, when this machine has one
rds("8.1", "protected-path", [
    ("real-bootvol-home-quoted", "rm -rf '{BOOTVOL_REAL}{REALHOME}'"),
    ("real-bootvol-trailing-slash", "rm -rf '{BOOTVOL_REAL}/'"),
    ("real-bootvol-find-escaped-spaces", "find {BOOTVOL_REAL_ESC}{REALHOME} -delete"),
], needs="bootvol")
ras("8.1", [
    ("real-bootvol-itself", "rm -rf '{BOOTVOL_REAL}'"),
    ("real-bootvol-tmp-below", "rm -rf '{BOOTVOL_REAL}/tmp/abc'"),
], needs="bootvol")
# 8.2 /System/Volumes is a system directory of its own
rds("8.2", "protected-path", [
    ("system-volumes", "rm -rf /System/Volumes"),
    ("system-volumes-slash", "rm -rf /System/Volumes/"),
    ("system-volumes-quoted", "rm -rf '/System/Volumes'"),
    ("data-volume-dotdot", "rm -rf /System/Volumes/Data/.."),
])
rds("8.2", "protected-glob", [("system-volumes-glob", "rm -rf /System/Vol*")])
ras("8.2", [
    ("preboot-below", "rm -rf /System/Volumes/Preboot/abc"),
    ("vm-below", "rm -rf /System/Volumes/VM/x"),
    ("data-volume-tmp-below", "rm -rf /System/Volumes/Data/tmp/abc"),
    ("update-below", "rm -rf /System/Volumes/Update/mnt1"),
])


# ===========================================================================
# Revision 3: variables and the working directory are judged by their possible values
# (spec "修订 3"). Commands are generic shapes of the safe patterns the revision-2 replay
# refused (no real paths, no project names). A rule tuple means either report is acceptable,
# because the spec does not say whether a name that was never assigned before a possibly-skipped
# assignment is read as "unknown" (expansion) or as "empty" (the rule of /, /* ...).
# ===========================================================================
R3_GROUP = {"1": "r3v", "2": "r3c"}
R3_COUNT = {}        # item -> [allow cases, deny cases]
R3_ITEMS = ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "2.1", "2.2", "2.3", "2.4", "2.5"]


def _r3(item, slug, cmd, expect, rule, cwd):
    group = R3_GROUP[item.split(".")[0]]
    c = R3_COUNT.setdefault(item, [0, 0])
    c[0 if expect == "allow" else 1] += 1
    _add(group, "%s-%s" % (item.replace(".", "_"), slug), cmd, expect, rule, cwd, None,
         ("r3", "r3:" + item), None, None)


def r3rows(item, rows, cwd="work"):
    """rows: (slug, cmd) = allow; (slug, cmd, rule) = deny; (slug, cmd, None, cwd) = allow with a cwd;
    (slug, cmd, rule, cwd) = deny with a cwd."""
    for row in rows:
        c = row[3] if len(row) > 3 else cwd
        if len(row) == 2 or row[2] is None:
            _r3(item, row[0], row[1], "allow", None, c)
        else:
            _r3(item, row[0], row[1], "deny", row[2], c)


_EG = ("expansion", "protected-glob")      # name read as unknown or as empty
_EP = ("expansion", "protected-path")

# 1.1 starting state: names this command never assigned are unknown; assigned names carry their possible values
r3rows("1.1", [
    ("never-assigned-quoted", 'rm -rf "$X"', "expansion"),
    ("other-name-assigned", 'A=/tmp/a; rm -rf "$B"', "expansion"),
    ("subpath-of-never-assigned", 'rm -rf "$E/sub"', "expansion"),
    ("rm-before-first-assignment", 'rm -rf "$d"; d=$(mktemp -d)', "expansion"),
    ("assigned-name-does-not-cover-another", 'd=$(mktemp -d); rm -rf "$d" "$e"', "expansion"),
    ("mktemp-assigned", 'd=$(mktemp -d); rm -rf "$d"'),
    ("literal-assigned", 'D=/tmp/x; rm -rf "$D"'),
    ("two-names-both-assigned", 'A=/tmp/a; B=/tmp/b; rm -rf "$A" "$B"'),
    ("set-e-prefix-mktemp", 'set -e; T=$(mktemp -d); cp a "$T/"; rm -rf "$T"'),
    ("non-recursive-unknown", 'rm -f "$X"'),
    ("function-body-after-mktemp", 'T=$(mktemp -d); run() { rm -rf "$T/m"; cp -R src "$T/m"; "$@"; }'),
])
# 1.2 a certain assignment replaces the whole set
r3rows("1.2", [
    ("unknown-replaced-by-literal", 'X=$HOME; X=/tmp/safe; rm -rf "$X"'),
    ("mktemp-replaced-by-literal", 'D=$(mktemp -d); D=/tmp/y; rm -rf "$D"'),
    ("cmdsubst-replaced-by-mktemp", 'd=$(cat f); d=$(mktemp -d); rm -rf "$d"'),
    ("newline-sequence", 'D=$HOME\nD=/tmp/x\nrm -rf "$D"'),
    ("empty-replaced-by-literal-subpath", 'D=; D=/tmp/x; rm -rf "$D"/sub'),
    ("literal-replaced-by-unknown", 'D=/tmp/x; D=$HOME; rm -rf "$D"', "expansion"),
    ("mktemp-replaced-by-root", 'd=$(mktemp -d); d=/; rm -rf "$d"', "protected-path"),
    ("literal-replaced-by-system-dir", 'D=/tmp/x; D=/usr; rm -rf "$D"', "protected-path"),
    ("literal-replaced-by-empty-glob", 'D=/tmp/x; D=; rm -rf "$D"/*', "protected-glob"),
    ("newline-replaced-by-cmdsubst", 'D=/tmp/x\nD=$(cat f)\nrm -rf "$D"', "expansion"),
])
# 1.3 an assignment that may not run is unioned into the old set;
#     an rm in the same && chain after the assignment counts as certain
r3rows("1.3", [
    ("cd-and-mktemp-chain-then-rm", 'cd {WORK}/sub && d=$(mktemp -d) && echo hi > "$d/x"; rm -rf "$d"'),
    ("cd-and-mktemp-newline-rm", 'cd {WORK} && d=$(mktemp -d) && echo hi > "$d/x"\nrm -rf "$d"'),
    ("cd-and-mktemp-env-prefix-install",
     'cd /tmp/proj && TH=$(mktemp -d) && HOME="$TH" bash install.sh; echo "RC=$?"; rm -rf "$TH"'),
    ("cd-and-mktemp-unquoted-target",
     'cd /tmp/proj && T=$(mktemp -d) && go build -o $T/bin ./cmd/x && echo hi > $T/token; rm -rf $T'),
    ("or-right-mktemp-quoted", '[ -d /tmp/x ] || d=$(mktemp -d); rm -rf "$d"'),
    ("if-adds-safe-literal", 'D=/tmp/a; if [ -n "$Q" ]; then D=/tmp/b; fi; rm -rf "$D"'),
    ("and-adds-safe-literal-subpath", 'D=/tmp/a; [ -n "$Q" ] && D=/tmp/b; rm -rf "$D"/sub'),
    ("case-adds-safe-literal", 'D=/tmp/a; case "$1" in x) D=/tmp/b;; esac; rm -rf "$D"'),
    ("maybe-empty-unquoted-vanishes", '[ -n "$Q" ] && D=/tmp/a; rm -rf $D'),
    ("rm-inside-the-same-and-chain", '[ -n "$Q" ] && X=/tmp/a && rm -rf "$X"/*'),
    ("and-adds-unknown", 'D=/tmp/a; [ -n "$Q" ] && D=$HOME; rm -rf "$D"', "expansion"),
    ("if-adds-system-dir", 'D=/tmp/a; if [ -n "$Q" ]; then D=/usr; fi; rm -rf "$D"', "protected-path"),
    ("or-adds-empty-then-glob", 'D=/tmp/a; [ -n "$Q" ] || D=; rm -rf "$D"/*', "protected-glob"),
    ("cd-and-mktemp-chain-then-glob", 'cd {WORK} && d=$(mktemp -d) && echo hi; rm -rf "$d"/*', _EG),
    ("cd-and-mktemp-chain-then-system-subpath", 'cd {WORK} && d=$(mktemp -d) && echo hi; rm -rf "$d/usr"', _EP),
    ("if-only-then-glob", 'if [ -d /tmp/x ]; then D=/tmp/x; fi; rm -rf "$D/"*', _EG),
    ("and-right-then-semicolon-glob", '[ -n "$CI" ] && X=/tmp/a; rm -rf "$X"/*', _EG),
    ("unknown-then-conditional-mktemp", 'D=$(cat f); [ -d "$D" ] || D=$(mktemp -d); rm -rf "$D"', "expansion"),
    ("unknown-then-conditional-literal",
     'X=$APP_HOME; if [ -d /nope ]; then X=/tmp/a; fi; rm -rf "$X"', "expansion"),
])
# 1.4 subshell, substitution, process substitution, pipeline segments do not change the outside
r3rows("1.4", [
    ("subshell-unknown-over-literal", 'D=/tmp/x; (D=$HOME); rm -rf "$D"'),
    ("subshell-system-dir-over-literal", 'D=/tmp/x; ( D=/usr; ls ); rm -rf "$D"'),
    ("backtick-root-over-literal", 'D=/tmp/x; echo `D=/; true`; rm -rf "$D"'),
    ("cmdsubst-root-over-mktemp", 'd=$(mktemp -d); X=$(d=/; echo hi); rm -rf "$d"'),
    ("brace-group-in-pipe-over-unknown", 'X=$HOME; { X=/tmp/safe; } | cat; rm -rf "$X"', "expansion"),
    ("cmdsubst-over-unknown", 'X=$HOME; echo $(X=/tmp/safe); rm -rf "$X"', "expansion"),
    ("procsubst-over-unknown", 'X=$HOME; cat <(X=/tmp/safe); rm -rf "$X"', "expansion"),
    ("spaced-subshell-over-unknown", 'X=$HOME; ( X=/tmp/safe ); rm -rf "$X"', "expansion"),
    ("backtick-over-unknown", 'X=$HOME; echo `X=/tmp/safe`; rm -rf "$X"', "expansion"),
    ("subshell-never-assigned-outside", '(D=/tmp/x); rm -rf "$D"/*', "expansion"),
])
# 1.5 substituting the possible values: empty quoted / unquoted, "$d/x", "$d"/*, literal, mktemp
r3rows("1.5", [
    ("empty-quoted-is-empty-argument", 'D=""; rm -rf "$D"'),
    ("empty-unquoted-vanishes", 'D=; rm -rf $D'),
    ("empty-unquoted-vanishes-next-target", 'D=""; rm -rf $D /tmp/abc'),
    ("empty-subpath-is-not-protected", 'D=""; rm -rf "$D/x"'),
    ("empty-braces-subpath-below-opt", 'D=; rm -rf "${D}/opt/foo"'),
    ("mktemp-subpath", 'd=$(mktemp -d); rm -rf "$d/a/b"'),
    ("literal-below-system-dir", 'D=/usr; rm -rf "$D/lib/foo"'),
    ("empty-then-glob-is-root-glob", 'D=""; rm -rf "$D"/*', "protected-glob"),
    ("empty-braces-slash-glob", 'D=; rm -rf "${D}/"*', "protected-glob"),
    ("empty-slash-is-root", 'D=""; rm -rf "$D/"', "protected-path"),
    ("empty-subpath-is-tmp", 'D=; rm -rf "$D/tmp"', "protected-path"),
    ("empty-subpath-is-usr-local", 'D=""; rm -rf "$D/usr/local"', "protected-path"),
    ("literal-system-dir", 'D=/usr; rm -rf "$D"', "protected-path"),
    ("literal-tmp-glob", 'D=/tmp; rm -rf "$D"/*', "protected-glob"),
    ("empty-next-to-unknown", 'D=""; rm -rf "$D" "$HOME"', "expansion"),
    ("mktemp-subpath-dotdot", 'd=$(mktemp -d); rm -rf "$d/../x"', "expansion"),
])
# 1.6 the same substitution for cd arguments, find start points and double-quoted nested text
r3rows("1.6", [
    ("cd-literal-var-then-star", 'D={WORK}/sub; cd "$D" && rm -rf *', None, "home"),
    ("cd-literal-var-unquoted-then-dot-star", 'D={WORK}/sub; cd $D && rm -rf ./*', None, "home"),
    ("cd-mktemp-then-star", 'd=$(mktemp -d) && cd "$d" && rm -rf *', None, "home"),
    ("find-literal-start-var", 'D=/tmp/x; find "$D" -name "*.o" -delete'),
    ("find-mktemp-start-var", 'd=$(mktemp -d) && find "$d" -name x -delete'),
    ("bash-c-dq-mktemp-subpath", 'd=$(mktemp -d); bash -c "rm -rf $d/sub"'),
    ("bash-c-dq-literal-tmp-subdir", 'D=/var/tmp/job; bash -c "rm -rf $D"'),
    ("cd-root-var-then-star", 'D=/; cd "$D" && rm -rf *', "protected-glob"),
    ("cd-home-var-then-dot", 'D={REALHOME}; cd "$D" && rm -rf .', "protected-path"),
    ("cd-subprocess-home-unquoted-var-then-dot-star", 'D={HOME}; cd $D && rm -rf ./*', "protected-glob"),
    ("cd-unknown-var-then-star", 'cd "$X" && rm -rf *', "unknown-cwd"),
    ("find-root-var", 'D=/; find "$D" -delete', "protected-path"),
    ("find-home-var", 'D={REALHOME}; find "$D" -name x -delete', "protected-path"),
    ("find-unknown-var", 'find "$X" -delete', "expansion"),
    ("bash-c-dq-empty-var-slash", 'D=""; bash -c "rm -rf $D/"', "protected-path"),
    ("sh-c-dq-etc-var", 'D=/etc; sh -c "rm -rf $D"', "protected-path"),
])

# 2.1 the starting cwd is the payload cwd; no cwd (or a relative one) is unknown
r3rows("2.1", [
    ("work-star", 'rm -rf *', None, "work"),
    ("none-named-targets", 'rm -rf ./build ./dist', None, "none"),
    ("none-cd-and-star", 'cd /tmp/x && rm -rf *', None, "none"),
    ("home-star", 'rm -rf *', "protected-glob", "home"),
    ("none-star", 'rm -rf *', "unknown-cwd", "none"),
    ("relative-dot", 'rm -rf .', "unknown-cwd", "relative"),
    ("none-semicolon-cd-star", 'cd /tmp/x; rm -rf *', "unknown-cwd", "none"),
    ("none-find-dot", 'find . -delete', "unknown-cwd", "none"),
])
# 2.2 "cd X && ...": inside the chain the cwd is X
r3rows("2.2", [
    ("literal-and-star", 'cd {WORK}/sub && rm -rf *', None, "home"),
    ("literal-and-dot-star", 'cd /tmp/proj && rm -rf ./*', None, "home"),
    ("two-cds-and-dot", 'cd {WORK} && cd sub && rm -rf .', None, "home"),
    ("literal-var-and-dot-star", 'D={WORK}/sub; cd "$D" && rm -rf ./*', None, "home"),
    ("and-build-then-sibling-dotdot", 'cd /tmp/proj && npm run build && rm -rf ../out/dist.bak', None, "home"),
    ("home-and-dot-star", 'cd {HOME} && rm -rf ./*', "protected-glob"),
    ("parent-of-home-and-dot", 'cd {REALHOME_PARENT} && rm -rf .', "protected-path"),
    ("tmp-subdir-and-dotdot", 'cd /tmp/x && rm -rf ..', "protected-path"),
    ("home-var-and-star", 'D={REALHOME}; cd "$D" && rm -rf *', "protected-glob"),
    ("unknown-and-dot", 'cd "$X" && rm -rf .', "unknown-cwd"),
    ("two-cds-up-to-root", 'cd /tmp/x && cd ../.. && rm -rf *', "protected-glob"),
    ("and-then-semicolon-keeps-old-cwd-possible", 'cd /tmp/x && make; rm -rf *', "protected-glob", "home"),
])
# 2.3 "cd X; ...", newline, "||", branch: the cwd afterwards is {old} + {new}
r3rows("2.3", [
    ("semicolon-star-both-safe", 'cd {WORK}/sub; rm -rf *'),
    ("newline-dot-star-both-safe", 'cd {WORK}/sub\nrm -rf ./*'),
    ("or-exit-dot-star-both-safe", 'cd /tmp/x || exit 1; rm -rf ./*'),
    ("newline-find-pyc", 'cd {WORK}/sub\nfind . -name "*.pyc" -delete'),
    ("semicolon-find-exec-rm", 'cd /tmp/p; find . -name __pycache__ -exec rm -rf {} +'),
    ("literal-var-newline-cd-find", 'R={WORK}/sub\ncd "$R"\nfind . -name x -exec rm -rf {} +'),
    ("unknown-cd-then-named", 'cd "$X"; rm -rf ./dist node_modules'),
    ("unknown-cd-or-exit-named", 'cd "$X" || exit 1; rm -rf out'),
    ("if-body-both-safe", 'if [ -d /tmp/x ]; then cd /tmp/x; fi; rm -rf ./*'),
    ("loop-body-both-safe", 'for d in a b; do cd /tmp/x; done; rm -rf *'),
    ("home-newline-find-delete", 'cd /tmp/x\nfind . -delete', "protected-path", "home"),
    ("home-semicolon-find-exec-rm", 'cd /tmp/p; find . -name x -exec rm -rf {} +', "protected-path", "home"),
    ("home-literal-var-find-delete", 'R={WORK}/sub\ncd "$R"\nfind . -delete', "protected-path", "home"),
    ("home-or-true-star", 'cd /tmp/x || true; rm -rf *', "protected-glob", "home"),
    ("home-if-body-find", 'if [ -d /tmp/x ]; then cd /tmp/x; fi; find . -name "*.o" -delete', "protected-path", "home"),
    ("none-semicolon-dotdot", 'cd /tmp/x; rm -rf ..', "unknown-cwd", "none"),
    ("none-newline-dot-star", 'cd /tmp/x\nrm -rf ./*', "unknown-cwd", "none"),
    ("none-semicolon-find", 'cd /tmp/x; find . -delete', "unknown-cwd", "none"),
    ("work-cd-home-semicolon-star", 'cd {HOME}; rm -rf *', "protected-glob"),
    ("unknown-cd-semicolon-dotdot", 'cd "$X"; rm -rf ..', "unknown-cwd"),
])
# 2.4 cd inside a subshell / substitution / process substitution / non-last pipe segment stays inside
r3rows("2.4", [
    ("subshell-cd-home-then-star", '(cd {HOME}); rm -rf *'),
    ("subshell-cd-home-ls-then-dot-star", '(cd {HOME} && ls); rm -rf ./*'),
    ("cmdsubst-cd-home-then-star", 'echo $(cd {HOME} && pwd); rm -rf *'),
    ("backtick-cd-root-then-named", 'echo `cd /; pwd`; rm -rf ./build'),
    ("star-inside-subshell-at-home", '(cd /tmp/x && rm -rf *)', None, "home"),
    ("spaced-subshell-then-dot-star", '( cd {WORK} ); rm -rf ./*', "protected-glob", "home"),
    ("quoted-cmdsubst-then-star", 'echo "$(cd /tmp/x && pwd)"; rm -rf *', "protected-glob", "home"),
    ("procsubst-then-star", 'cat <(cd /tmp/x; ls); rm -rf *', "protected-glob", "home"),
    ("brace-in-pipe-then-find", '{ cd /tmp/x; ls; } | cat; find . -delete', "protected-path", "home"),
])
# 2.5 a relative target is judged once per possible cwd; one protected or unknown possibility is enough to refuse
r3rows("2.5", [
    ("two-literals-both-safe", 'cd /tmp/a; cd /tmp/b; rm -rf *'),
    ("or-true-literal-both-safe", 'cd {WORK}/sub || true; rm -rf ./*'),
    ("unknown-cwd-concrete-names", 'cd "$X"; rm -rf build dist ./out'),
    ("literal-concrete-names", 'cd /tmp/x; rm -rf build dist ./out'),
    ("new-possibility-is-home", 'cd {HOME} || true; rm -rf ./*', "protected-glob"),
    ("new-possibility-is-tilde", 'cd ~; rm -rf *', "protected-glob"),
    ("old-possibility-is-home", 'cd {WORK} || true; rm -rf .', "protected-path", "home"),
    ("old-possibility-is-unknown", 'cd {WORK} || true; rm -rf .', "unknown-cwd", "none"),
    ("chain-of-unions-includes-home", 'cd /tmp/a; cd /tmp/b; rm -rf *', "protected-glob", "home"),
    ("new-possibility-is-unknown-dotdot-sub", 'cd "$X" || true; rm -rf ../y', "unknown-cwd"),
])


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
class Ctx:
    def __init__(self, base, direct):
        self.base = base
        self.home = os.path.join(base, "home")
        self.work = os.path.join(base, "work")
        os.makedirs(self.home)
        os.makedirs(self.work)
        os.makedirs(os.path.join(self.work, "sub"))
        self.direct = direct
        self.realhome = pwd.getpwuid(os.getuid()).pw_dir.rstrip("/") or "/"
        self.realhome_parent = os.path.dirname(self.realhome) or "/"
        self.realhome_dslash = self.realhome_parent.rstrip("/") + "//" + os.path.basename(self.realhome)
        self._init_rev2()

    def _init_rev2(self):
        comps = [c for c in self.realhome.split("/") if c]
        name = comps[-1] if comps else ""
        self.name_ok = len(name) >= 3 and len(comps) >= 1
        n = name if self.name_ok else "abc"
        last = n[-1]
        seq_end = chr(ord(last) + 1) if last < "z" else chr(ord(last) - 1)
        first = comps[0] if comps else "Users"
        rest = "/".join(comps[1:])
        self.rev2 = {
            "{RN_PSTAR}": n[:-1] + "*",
            "{RN_LASTBR}": n[:-1] + "[" + last + "]",
            "{RN_MID2}": n[:2] + "*" + n[-2:],
            "{RN_SEQ2}": n[:-1] + "{" + (last + ".." + seq_end if last < "z" else seq_end + ".." + last) + "}",
            "{RN_SEQ}": n[:-1] + "{" + last + ".." + last + "}",
            "{RN_BR}": n[0] + "[" + n[1] + "]" + n[2:],
            "{RN_Q}": n[:-1] + "?",
            "{RN2}": n[:2],
            "{RN3}": n[:3],
            "{RN}": n,
            "{RL0B}": "/" + first[:2] + "*" + first[-2:] + ("/" + rest if rest else ""),
            "{RL0}": "/" + first[:2] + "*" + ("/" + rest if rest else ""),
        }
        # symlinks inside the temporary directory (never followed by cleanup: unlinked explicitly)
        self.links = {}
        for key, target in (("{BOOTLINK}", "/"), ("{HOMELINK}", self.realhome),
                            ("{USRLINK}", "/usr"), ("{USERSLINK}", self.realhome_parent)):
            if os.path.isdir(target):
                path = os.path.join(self.base, "link-" + key.strip("{}").lower())
                os.symlink(target, path)
                self.links[key] = path
        # a /Volumes entry that resolves to / (macOS startup volume alias), probed at run time
        self.bootvol = None
        try:
            for entry in sorted(os.listdir("/Volumes")):
                full = os.path.join("/Volumes", entry)
                if os.path.islink(full) and os.path.realpath(full) == "/":
                    self.bootvol = full
                    break
        except OSError:
            pass

    def cleanup_links(self):
        for path in self.links.values():
            try:
                os.unlink(path)
            except OSError:
                pass

    def argv(self):
        if self.direct:
            return [sys.executable, HOOK_PATH]
        return ["sh", RUN_GUARD, HOOK_NAME]

    def env(self, home=None):
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("CLAUDE_ALLOW_") or k in ("SENSITIVE_GUARD_TIMEOUT", "RM_GUARD_LANG"):
                del env[k]
        env["HOME"] = home or self.home
        env["PYTHONDONTWRITEBYTECODE"] = "1"  # Apple's python 3.9 would otherwise write a bytecode cache under HOME/Library
        return env

    def subst(self, s):
        for k, v in (("{REALHOME_DSLASH}", self.realhome_dslash),
                     ("{REALHOME_PARENT}", self.realhome_parent),
                     ("{REALHOME}", self.realhome)):
            s = s.replace(k, v)
        for k, v in self.rev2.items():
            s = s.replace(k, v)
        for k, v in self.links.items():
            s = s.replace(k, v)
        if self.bootvol:
            s = s.replace("{BOOTVOL_REAL_ESC}", self.bootvol.replace(" ", "\\ "))
            s = s.replace("{BOOTVOL_REAL}", self.bootvol)
        s = s.replace("{BASE}", self.base)
        s = re.sub(r"(?<!\$)\{HOME\}", lambda m: self.home, s)
        s = re.sub(r"(?<!\$)\{WORK\}", lambda m: self.work, s)
        return s

    def cwd_value(self, spec):
        """Returns (present, value) for the payload."""
        if spec == "none":
            return False, None
        if spec == "work":
            return True, self.work
        if spec == "home":
            return True, self.home
        if spec == "relative":
            return True, "relative/some/dir"
        return True, self.subst(spec)


def invoke(ctx, stdin_bytes, home=None, timeout=CASE_TIMEOUT):
    """Run the hook once. Returns (rc, stdout, stderr, seconds). rc None on timeout."""
    t0 = time.time()
    p = subprocess.Popen(ctx.argv(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, env=ctx.env(home), cwd=ctx.work,
                         start_new_session=True)
    try:
        out, err = p.communicate(stdin_bytes, timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass
        p.communicate()
        return None, b"", b"", time.time() - t0
    finally:
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            p.wait()
    return p.returncode, out, err, time.time() - t0


def payload_for(ctx, cmd, cwd_spec):
    obj = {"tool_input": {"command": cmd}}
    present, val = ctx.cwd_value(cwd_spec)
    if present:
        obj["cwd"] = val
    return json.dumps(obj).encode("utf-8")


RULE_LINE = re.compile(r"^rule=(\S+)$", re.M)


def check_deny_output(rc, out, err, rule, target=None):
    """Return None when the deny output follows the contract, else a reason string."""
    if rc != 2:
        return "exit code %r, want 2 (stdout=%r stderr=%r)" % (rc, out[:120], err[:120])
    text = out.decode("utf-8", "replace")
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) != 1:
        return "stdout should be one JSON line, got %d lines" % len(lines)
    try:
        obj = json.loads(lines[0])
        hso = obj["hookSpecificOutput"]
    except Exception as e:
        return "stdout is not the expected JSON: %r" % (e,)
    if hso.get("hookEventName") != "PreToolUse":
        return "hookEventName is %r" % (hso.get("hookEventName"),)
    if hso.get("permissionDecision") != "deny":
        return "permissionDecision is %r" % (hso.get("permissionDecision"),)
    reason = hso.get("permissionDecisionReason")
    if not isinstance(reason, str) or not reason:
        return "permissionDecisionReason missing"
    if not reason.split("\n", 1)[0].startswith("已拒绝:"):
        return "reason first line does not start with 已拒绝: (%r)" % reason.split("\n", 1)[0][:60]
    found = RULE_LINE.findall(reason)
    if len(found) != 1:
        return "reason has %d rule= lines, want 1" % len(found)
    if rule is not None:
        wanted = (rule,) if isinstance(rule, str) else tuple(rule)
        if found[0] not in wanted:
            return "rule=%s, want %s" % (found[0], " or ".join(wanted))
    if found[0] == "expansion" and EXPANSION_PHRASE not in reason:
        return "expansion reason lacks the phrase about new shells"
    if target is not None and target not in reason:
        return "reason does not mention target %r" % target
    if err.decode("utf-8", "replace").strip() != reason.strip():
        if reason.strip() not in err.decode("utf-8", "replace"):
            return "stderr does not carry the same reason"
    return None


def skip_reason(case, ctx):
    """Why a case cannot run on this machine, or None."""
    if case.get("only") == "darwin" and sys.platform != "darwin":
        return "needs macOS (path case folding is macOS only)"
    if case.get("needs") == "bootvol" and not ctx.bootvol:
        return "no /Volumes entry resolves to /; the symlink variants in {BOOTLINK} cases still run"
    text = case["cmd"] + " " + str(case["cwd"])
    if ("{RN" in text or "{RL0" in text) and not ctx.name_ok:
        return "home directory name %r is shorter than 3 characters" % os.path.basename(ctx.realhome)
    for key in ("{BOOTLINK}", "{HOMELINK}", "{USRLINK}", "{USERSLINK}"):
        if key in text and key not in ctx.links:
            return "cannot create the %s symlink on this machine" % key
    return None


def run_case(case, ctx):
    try:
        why_skip = skip_reason(case, ctx)
        if why_skip:
            return "skip", why_skip
        if not os.path.isfile(HOOK_PATH):
            return False, "hook file missing: %s" % HOOK_PATH
        cmd = ctx.subst(case["cmd"])
        rc, out, err, _ = invoke(ctx, payload_for(ctx, cmd, case["cwd"]))
        if rc is None:
            return False, "timed out after %ds" % CASE_TIMEOUT
        if case["expect"] == "allow":
            if rc != 0:
                return False, "exit code %r, want 0 (stderr=%r)" % (rc, err[:160])
            if out.strip():
                return False, "stdout not empty: %r" % out[:160]
            return True, ""
        why = check_deny_output(rc, out, err, case["rule"], case["target"])
        return (why is None), (why or "")
    except Exception as e:
        return False, "runner error: %r" % (e,)


# ---------------------------------------------------------------------------
# separately asserted behaviours
# ---------------------------------------------------------------------------
def special(sid, tags=()):
    def deco(fn):
        SPECIALS.append({"id": sid, "fn": fn, "tags": ("special",) + tuple(tags)})
        return fn
    return deco


def _need_hook():
    if not os.path.isfile(HOOK_PATH):
        return "hook file missing: %s" % HOOK_PATH
    return None


@special("special01-expansion-phrase", ("miss2",))
def sp_phrase(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    rc, out, err, _ = invoke(ctx, payload_for(ctx, 'rm -rf "$UNSET_X/sub"', "work"))
    if rc != 2:
        return False, "exit code %r" % (rc,)
    if EXPANSION_PHRASE not in out.decode("utf-8", "replace"):
        return False, "stdout reason lacks the phrase"
    if EXPANSION_PHRASE not in err.decode("utf-8", "replace"):
        return False, "stderr reason lacks the phrase"
    return True, ""


def _log_path(home):
    return os.path.join(home, ".claude", "hooks", "rm-guard.log")


@special("special02-deny-log")
def sp_log(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    home = os.path.join(ctx.base, "loghome")
    os.makedirs(home)
    log = _log_path(home)
    if os.path.exists(log):
        return False, "log should not exist before the first denial"
    denies = [('rm -rf "$X"', "expansion"), ("rm -rf ~/x", "tilde"), ("rm -rf /Users", "protected-path")]
    for i, (cmd, rule) in enumerate(denies, 1):
        rc, out, err, _ = invoke(ctx, payload_for(ctx, cmd, "work"), home=home)
        if rc != 2:
            return False, "denial %d: exit code %r" % (i, rc)
        if not os.path.isfile(log):
            return False, "denial %d: log file not created at %s" % (i, log)
        mode = stat.S_IMODE(os.stat(log).st_mode)
        if mode != 0o600:
            return False, "log mode is %o, want 600" % mode
        with open(log, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        if len(lines) != i:
            return False, "after denial %d the log has %d lines" % (i, len(lines))
        if rule not in lines[-1]:
            return False, "last log line lacks rule %s: %r" % (rule, lines[-1][:120])
        if not re.search(r"\d{4}-\d{2}-\d{2}", lines[-1]):
            return False, "last log line has no UTC date: %r" % lines[-1][:120]
    rc, out, err, _ = invoke(ctx, payload_for(ctx, "rm -rf /tmp/abc", "work"), home=home)
    if rc != 0:
        return False, "allowed command exit code %r" % (rc,)
    with open(log, encoding="utf-8", errors="replace") as f:
        if len(f.read().splitlines()) != len(denies):
            return False, "an allowed command added a log line"
    return True, ""


@special("special03-log-target-truncated")
def sp_log_trunc(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    home = os.path.join(ctx.base, "loghome-trunc")
    os.makedirs(home)
    cmd = 'rm -rf "$V_' + "x" * 400 + '"'
    rc, out, err, _ = invoke(ctx, payload_for(ctx, cmd, "work"), home=home)
    if rc != 2:
        return False, "exit code %r" % (rc,)
    log = _log_path(home)
    if not os.path.isfile(log):
        return False, "log not created"
    with open(log, encoding="utf-8", errors="replace") as f:
        data = f.read()
    if len(data.splitlines()) != 1:
        return False, "want one log line, got %d" % len(data.splitlines())
    if "x" * 201 in data:
        return False, "target is not cut to 200 characters in the log"
    if "x" * 100 not in data:
        return False, "log line does not carry the target text"
    return True, ""


@special("special04-log-failure-still-denies")
def sp_log_fail(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    home = os.path.join(ctx.base, "loghome-broken")
    os.makedirs(home)
    with open(os.path.join(home, ".claude"), "w") as f:  # a file where the directory should be
        f.write("not a directory")
    rc, out, err, _ = invoke(ctx, payload_for(ctx, 'rm -rf "$X"', "work"), home=home)
    why = check_deny_output(rc, out, err, "expansion")
    return (why is None), (why or "")


@special("special05-log-dir-created")
def sp_log_dir(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    home = os.path.join(ctx.base, "loghome-nodir")
    os.makedirs(home)
    if os.path.exists(os.path.join(home, ".claude")):
        return False, "setup: .claude should not exist"
    rc, _, _, _ = invoke(ctx, payload_for(ctx, "rm -rf ~", "work"), home=home)
    if rc != 2:
        return False, "exit code %r" % (rc,)
    if not os.path.isdir(os.path.join(home, ".claude", "hooks")):
        return False, "hooks directory not created"
    return True, ""


def _expect_pass_through(ctx, stdin_bytes):
    miss = _need_hook()
    if miss:
        return False, miss
    rc, out, err, _ = invoke(ctx, stdin_bytes)
    if rc != 0:
        return False, "exit code %r, want 0 (stderr=%r)" % (rc, err[:160])
    if out.strip():
        return False, "stdout not empty: %r" % out[:160]
    return True, ""


@special("special06-input-not-json")
def sp_not_json(ctx):
    return _expect_pass_through(ctx, b"this is not json")


@special("special07-input-empty-stdin")
def sp_empty_stdin(ctx):
    return _expect_pass_through(ctx, b"")


@special("special08-input-no-command")
def sp_no_command(ctx):
    for body in (b"{}", b'{"tool_input":{}}', b'{"tool_input":{"command":null}}',
                 b'{"tool_input":{"command":123}}', b'{"tool_input":"x"}', b"[]", b"null"):
        ok, why = _expect_pass_through(ctx, body)
        if not ok:
            return False, "%r: %s" % (body, why)
    return True, ""


@special("special09-input-empty-command")
def sp_empty_command(ctx):
    for cmd in ("", "   ", "\n"):
        ok, why = _expect_pass_through(ctx, json.dumps({"tool_input": {"command": cmd}, "cwd": ctx.work}).encode())
        if not ok:
            return False, "%r: %s" % (cmd, why)
    return True, ""


@special("special10-big-doc-heredoc-fast", ("miss5",))
def sp_big_heredoc(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    line = 'rm -rf "$HOME" and rm -rf $X ~/x /*  复盘:变量没设,展开成空\n'
    body = ""
    while len(body.encode("utf-8")) < 100 * 1024:
        body += line
    cmd = "cat > a.md <<EOF\n" + body + "EOF"
    rc, out, err, secs = invoke(ctx, payload_for(ctx, cmd, "work"))
    if rc != 0:
        return False, "exit code %r, want 0 (stderr=%r)" % (rc, err[:160])
    if out.strip():
        return False, "stdout not empty"
    if secs >= 1.0:  # revision 2 item 7.2 / spec section 5: 1 second (was 3)
        return False, "took %.2fs, want < 1s" % secs
    return True, ""


JUDGE_SCRIPT = r"""
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("rm_guard_hook_under_test", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
out = []
for cmd, cwd in json.loads(sys.argv[2]):
    r = m.judge(cmd, cwd)
    out.append(None if r is None else [r[0], r[1]])
print(json.dumps(out))
"""


def run_judge(ctx, items, home, drop_home=False):
    env = ctx.env(home)
    if drop_home:
        env.pop("HOME", None)
    p = subprocess.Popen([sys.executable, "-c", JUDGE_SCRIPT, HOOK_PATH, json.dumps(items)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=env, cwd=ctx.work, start_new_session=True)
    try:
        out, err = p.communicate(timeout=CASE_TIMEOUT)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass
        p.communicate()
        return None, "timed out"
    if p.returncode != 0:
        return None, "python exit %r: %s" % (p.returncode, err.decode("utf-8", "replace")[-300:])
    try:
        return json.loads(out.decode("utf-8").strip().splitlines()[-1]), ""
    except Exception as e:
        return None, "unparsable output %r: %r" % (out[:200], e)


@special("special11-import-has-no-side-effects")
def sp_import(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    home = os.path.join(ctx.base, "importhome")
    os.makedirs(home)
    res, why = run_judge(ctx, [['rm -rf "$X"', None], ["rm -rf /tmp/abc", ctx.work]], home)
    if res is None:
        return False, why
    if os.listdir(home):
        return False, "import/judge wrote into HOME: %r" % os.listdir(home)
    return True, ""


@special("special12-judge-return-contract")
def sp_judge_contract(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    home = os.path.join(ctx.base, "judgehome")
    os.makedirs(home)
    items = [['rm -rf "$X"', ctx.work], ["rm -rf /tmp/abc", ctx.work], ["rm -rf ~/x", ctx.work],
             ["rm -rf /Users", ctx.work], ["rm -rf *", home], ["rm -rf .", None], ["rm -rf .", ctx.work],
             ['rm -rf "$HOME', ctx.work]]
    res, why = run_judge(ctx, items, home)
    if res is None:
        return False, why
    want = ["expansion", None, "tilde", "protected-path", "protected-glob", "unknown-cwd", None, "unparsable"]
    for item, r, w in zip(items, res, want):
        got = None if r is None else r[0]
        if got != w:
            return False, "judge(%r, %r) -> %r, want rule %r" % (item[0], item[1], r, w)
        if r is not None and (not isinstance(r[1], str) or not r[1]):
            return False, "judge(%r) target is not a non-empty string: %r" % (item[0], r)
    if "$X" not in res[0][1]:
        return False, "target of the expansion case does not carry $X: %r" % (res[0][1],)
    if "~/x" not in res[2][1]:
        return False, "target of the tilde case does not carry ~/x: %r" % (res[2][1],)
    return True, ""


@special("special13-judge-home-sources")
def sp_judge_home(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    home = os.path.join(ctx.base, "judgehome2")
    os.makedirs(home)
    items = [["rm -rf " + ctx.realhome, ctx.work], ["rm -rf " + home, ctx.work]]
    res, why = run_judge(ctx, items, home)  # HOME env differs from the pwd record: both count
    if res is None:
        return False, why
    for item, r in zip(items, res):
        if r is None or r[0] != "protected-path":
            return False, "HOME set: judge(%r) -> %r, want protected-path" % (item[0], r)
    res, why = run_judge(ctx, items[:1], home, drop_home=True)  # no HOME: pwd record alone
    if res is None:
        return False, why
    if res[0] is None or res[0][0] != "protected-path":
        return False, "HOME unset: judge(real home) -> %r, want protected-path" % (res[0],)
    return True, ""


# ===========================================================================
# Revision 2 separate checks: exception paths (5.3 / 7.2), log (6.1 / 6.2),
# speed (7.2), self checks (7.1). Helper scripts run in a subprocess with a
# temporary HOME; nothing here executes a delete.
# ===========================================================================
PATCH_SCRIPT = r"""
import importlib.util, io, json, os, sys
spec = importlib.util.spec_from_file_location("rm_guard_hook_under_test", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
job = json.loads(sys.argv[2])
real_out = sys.__stdout__

def boom(*a, **k):
    raise RuntimeError("injected failure")

def finish(obj):
    real_out.write(json.dumps(obj) + "\n")
    real_out.flush()
    sys.exit(0)

for name in job.get("patch", []):
    if name == "run":
        if not hasattr(m, "Analyzer") or not hasattr(m.Analyzer, "run"):
            finish({"error": "hook has no Analyzer.run to patch"})
        m.Analyzer.run = boom
    elif name == "text":
        if not hasattr(m, "text_rule"):
            finish({"error": "hook has no text_rule to patch"})
        m.text_rule = boom
    elif name == "log":
        os.open = boom
        os.makedirs = boom

class BrokenBuffer(object):
    def write(self, data):
        raise BrokenPipeError("injected broken pipe")
    def flush(self):
        raise BrokenPipeError("injected broken pipe")

class Sink(object):
    def __init__(self, broken):
        self.buffer = BrokenBuffer() if broken else io.BytesIO()
    def write(self, s):
        if isinstance(self.buffer, BrokenBuffer):
            self.buffer.write(s)
        self.buffer.write(s.encode("utf-8"))
    def flush(self):
        self.buffer.flush()

res = {}
if job["kind"] == "judge":
    try:
        r = m.judge(job["cmd"], job.get("cwd"))
        res["judge"] = None if r is None else [r[0], r[1]]
    except BaseException as e:
        res["raised"] = repr(e)
else:
    payload = json.dumps({"tool_input": {"command": job["cmd"]}, "cwd": job.get("cwd")}).encode("utf-8")
    class Stdin(object):
        buffer = io.BytesIO(payload)
        def read(self):
            return payload.decode("utf-8")
    sys.stdin = Stdin()
    out, err = Sink(job.get("broken_out", False)), Sink(job.get("broken_err", False))
    sys.stdout, sys.stderr = out, err
    try:
        rc = m.main()
    except SystemExit as e:
        rc = e.code
    except BaseException as e:
        rc = "raised " + repr(e)
    sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
    res["rc"] = rc
    res["out"] = out.buffer.getvalue().decode("utf-8", "replace") if isinstance(out.buffer, io.BytesIO) else ""
    res["err"] = err.buffer.getvalue().decode("utf-8", "replace") if isinstance(err.buffer, io.BytesIO) else ""
    log = getattr(m, "LOG_PATH", os.path.join(os.environ.get("HOME", ""), ".claude", "hooks", "rm-guard.log"))
    try:
        with open(log, encoding="utf-8", errors="replace") as f:
            res["log"] = f.read()
    except OSError:
        res["log"] = None
finish(res)
"""

PERF_SCRIPT = r"""
import importlib.util, json, statistics, sys, time
spec = importlib.util.spec_from_file_location("rm_guard_hook_under_test", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
out = []
for cmd, cwd in json.loads(sys.argv[2]):
    ts = []
    for _ in range(20):
        t = time.perf_counter()
        m.judge(cmd, cwd)
        ts.append(time.perf_counter() - t)
    out.append(statistics.median(ts))
print(json.dumps(out))
"""


def run_helper(ctx, script, arg, home):
    p = subprocess.Popen([sys.executable, "-c", script, HOOK_PATH, arg],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=ctx.env(home), cwd=ctx.work, start_new_session=True)
    try:
        out, err = p.communicate(timeout=CASE_TIMEOUT)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass
        p.communicate()
        return None, "timed out"
    if p.returncode != 0:
        return None, "python exit %r: %s" % (p.returncode, err.decode("utf-8", "replace")[-300:])
    try:
        res = json.loads(out.decode("utf-8").strip().splitlines()[-1])
    except Exception as e:
        return None, "unparsable output %r: %r" % (out[:200], e)
    if "error" in res:
        return None, res["error"]
    return res, ""


def _fresh_home(ctx, name):
    home = os.path.join(ctx.base, name)
    os.makedirs(home)
    return home


def _patched_judge(ctx, name, patch, cmd):
    home = _fresh_home(ctx, name)
    return run_helper(ctx, PATCH_SCRIPT, json.dumps({"kind": "judge", "patch": patch, "cmd": cmd, "cwd": ctx.work}), home)


def _patched_main(ctx, name, patch, cmd, **extra):
    home = _fresh_home(ctx, name)
    job = {"kind": "main", "patch": patch, "cmd": cmd, "cwd": ctx.work}
    job.update(extra)
    res, why = run_helper(ctx, PATCH_SCRIPT, json.dumps(job), home)
    return res, why


# 5.3 / 7.2: judge raises -> text rule; text rule raises -> deny (unparsable)
@special("special14-exception-in-analysis-uses-text-rule-via-judge", ("r2", "r2:5.3", "r2:7.2"))
def sp_exc_judge_text(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    rows = [('rm -rf "$X"', "unparsable"), ("rm -rf ~/x", "unparsable"), ('find "$X" -delete', "unparsable"),
            ("rm -rf " + ctx.realhome, "unparsable"), ("rm -rf /tmp/abc", None), ("echo hi", None),
            ("rm -f \"$X\"", None)]
    for i, (cmd, want) in enumerate(rows):
        res, why = _patched_judge(ctx, "exc-judge-%d" % i, ["run"], cmd)
        if res is None:
            return False, why
        if "raised" in res:
            return False, "judge(%r) raised %s instead of falling back to the text rule" % (cmd, res["raised"])
        got = res["judge"][0] if res["judge"] else None
        if got != want:
            return False, "judge(%r) with the analysis raising -> %r, want %r" % (cmd, res["judge"], want)
    return True, ""


@special("special15-exception-in-text-rule-denies-via-judge", ("r2", "r2:5.3", "r2:7.2"))
def sp_exc_judge_deny(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    for i, cmd in enumerate(['rm -rf "$X"', "rm -rf /tmp/abc", "rm -rf build", "sudo rm -rf ./dist"]):
        res, why = _patched_judge(ctx, "exc-both-%d" % i, ["run", "text"], cmd)
        if res is None:
            return False, why
        if "raised" in res:
            return False, "judge(%r) raised %s; it must return a rejection" % (cmd, res["raised"])
        if not res["judge"] or res["judge"][0] != "unparsable":
            return False, "judge(%r) with analysis and text rule raising -> %r, want unparsable" % (cmd, res["judge"])
        if not isinstance(res["judge"][1], str):
            return False, "rejection target is not a string: %r" % (res["judge"],)
    return True, ""


def _check_deny_main(res, why, want_rule, want_log):
    if res is None:
        return False, why
    if res["rc"] != 2:
        return False, "main() returned %r, want 2 (out=%r err=%r)" % (res["rc"], res["out"][:100], res["err"][:100])
    if want_rule:
        reason = None
        try:
            reason = json.loads(res["out"].strip().splitlines()[-1])["hookSpecificOutput"]["permissionDecisionReason"]
        except Exception as e:
            return False, "stdout is not the deny JSON: %r" % (res["out"][:100],)
        if "rule=" + want_rule not in reason:
            return False, "reason lacks rule=%s: %r" % (want_rule, reason[:160])
    if want_log:
        if not res["log"] or want_log not in res["log"]:
            return False, "log lacks %r: %r" % (want_log, res["log"])
    return True, ""


@special("special16-exception-in-analysis-exit-code-via-main", ("r2", "r2:5.3", "r2:7.2"))
def sp_exc_main_text(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    res, why = _patched_main(ctx, "exc-main-1", ["run"], 'rm -rf "$X"')
    ok, msg = _check_deny_main(res, why, "unparsable", "unparsable")
    if not ok:
        return False, "var target: " + msg
    res, why = _patched_main(ctx, "exc-main-2", ["run"], "rm -rf ~/x")
    ok, msg = _check_deny_main(res, why, "unparsable", "unparsable")
    if not ok:
        return False, "tilde target: " + msg
    res, why = _patched_main(ctx, "exc-main-3", ["run"], "rm -rf /tmp/abc")
    if res is None:
        return False, why
    if res["rc"] != 0 or res["out"].strip():
        return False, "safe command with the analysis raising: rc=%r out=%r" % (res["rc"], res["out"][:100])
    return True, ""


@special("special17-exception-in-text-rule-exit-code-via-main", ("r2", "r2:5.3", "r2:7.2"))
def sp_exc_main_deny(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    for i, cmd in enumerate(['rm -rf "$X"', "rm -rf /tmp/abc", "rm -rf build"]):
        res, why = _patched_main(ctx, "exc-main-both-%d" % i, ["run", "text"], cmd)
        ok, msg = _check_deny_main(res, why, "unparsable", "unparsable")
        if not ok:
            return False, "%r: %s" % (cmd, msg)
    return True, ""


@special("special18-broken-stdout-still-exit-2", ("r2", "r2:5.3"))
def sp_broken_stdout(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    for i, cmd in enumerate(['rm -rf "$X"', "rm -rf ~", "rm -rf /usr"]):
        res, why = _patched_main(ctx, "broken-out-%d" % i, [], cmd, broken_out=True)
        if res is None:
            return False, why
        if res["rc"] != 2:
            return False, "%r with a broken stdout: main() returned %r, want 2" % (cmd, res["rc"])
    return True, ""


@special("special19-broken-stderr-still-exit-2", ("r2", "r2:5.3"))
def sp_broken_stderr(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    for i, cmd in enumerate(['rm -rf "$X"', "rm -rf ~", "rm -rf /usr"]):
        res, why = _patched_main(ctx, "broken-err-%d" % i, [], cmd, broken_err=True)
        if res is None:
            return False, why
        if res["rc"] != 2:
            return False, "%r with a broken stderr: main() returned %r, want 2" % (cmd, res["rc"])
    res, why = _patched_main(ctx, "broken-both", [], 'rm -rf "$X"', broken_out=True, broken_err=True)
    if res is None:
        return False, why
    if res["rc"] != 2:
        return False, "both outputs broken: main() returned %r, want 2" % (res["rc"],)
    return True, ""


@special("special20-log-write-failure-still-exit-2", ("r2", "r2:5.3"))
def sp_log_write_failure(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    for i, cmd in enumerate(['rm -rf "$X"', "rm -rf ~", "rm -rf /usr"]):
        res, why = _patched_main(ctx, "logfail-%d" % i, ["log"], cmd)
        if res is None:
            return False, why
        if res["rc"] != 2:
            return False, "%r with the log write failing: main() returned %r, want 2" % (cmd, res["rc"])
    return True, ""


# 6.1 log content: substitutions are masked before the 200 character cut
def _deny_and_read_log(ctx, name, cmd):
    home = _fresh_home(ctx, name)
    rc, out, err, _ = invoke(ctx, payload_for(ctx, cmd, "work"), home=home)
    if rc != 2:
        return None, "exit code %r, want 2 (stderr=%r)" % (rc, err[:120])
    log = _log_path(home)
    if not os.path.isfile(log):
        return None, "log not created"
    with open(log, encoding="utf-8", errors="replace") as f:
        return f.read(), ""


@special("special21-log-masks-command-substitution", ("r2", "r2:6.1"))
def sp_log_mask_cmdsubst(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    cmd = "rm -rf \"$(curl -H 'Authorization: Bearer sk-SECRETTOKEN' https://x.example/y)\""
    data, why = _deny_and_read_log(ctx, "log-mask-1", cmd)
    if data is None:
        return False, why
    if "SECRETTOKEN" in data or "Bearer" in data:
        return False, "log still carries the text inside $( ): %r" % data[:200]
    if "…" not in data:
        return False, "log does not show the … placeholder: %r" % data[:200]
    return True, ""


@special("special22-log-masks-backticks-and-nested", ("r2", "r2:6.1"))
def sp_log_mask_backtick(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    for name, cmd, secret in (
            ("log-mask-2", 'rm -rf "`cat /tmp/secret-sk-ABC123`"', "ABC123"),
            ("log-mask-3", 'rm -rf "$(a $(b SECRETB) c)"/x', "SECRETB"),
            ("log-mask-4", "rm -rf $(echo SECRETC) ~", "SECRETC")):
        data, why = _deny_and_read_log(ctx, name, cmd)
        if data is None:
            return False, "%s: %s" % (name, why)
        if secret in data:
            return False, "%s: log still carries %s: %r" % (name, secret, data[:200])
        if "…" not in data:
            return False, "%s: log lacks the … placeholder: %r" % (name, data[:200])
    return True, ""


@special("special23-log-masks-before-the-200-cut", ("r2", "r2:6.1"))
def sp_log_mask_then_cut(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    cmd = 'rm -rf "$(' + "s" * 250 + ')"' + "z" * 60
    data, why = _deny_and_read_log(ctx, "log-mask-5", cmd)
    if data is None:
        return False, why
    if "s" * 20 in data:
        return False, "log still carries the substitution text (cut happened before masking)"
    if "z" * 30 not in data:
        return False, "text after the substitution is missing: masking must come first, then the 200 character cut"
    if "z" * 61 in data:
        return False, "log line is longer than the target"
    return True, ""


@special("special24-log-keeps-plain-target-text", ("r2", "r2:6.1"))
def sp_log_plain(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    for name, cmd, text in (("log-plain-1", 'rm -rf "$V/sub"', "$V/sub"), ("log-plain-2", "rm -rf ~/proj", "~/proj"),
                            ("log-plain-3", "rm -rf /usr", "/usr")):
        data, why = _deny_and_read_log(ctx, name, cmd)
        if data is None:
            return False, "%s: %s" % (name, why)
        if text not in data:
            return False, "%s: log lacks the plain target %r: %r" % (name, text, data[:160])
    return True, ""


# 6.2 log directory 700, log file 600 on every write, no symlink following
def _hooks_dir(home):
    return os.path.join(home, ".claude", "hooks")


@special("special25-log-dir-created-700", ("r2", "r2:6.2"))
def sp_log_dir_700(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    for i, cmd in enumerate(['rm -rf "$X"', "rm -rf ~", "rm -rf /usr"]):
        home = _fresh_home(ctx, "log700-%d" % i)
        rc, _, _, _ = invoke(ctx, payload_for(ctx, cmd, "work"), home=home)
        if rc != 2:
            return False, "%r: exit code %r" % (cmd, rc)
        mode = stat.S_IMODE(os.stat(_hooks_dir(home)).st_mode)
        if mode != 0o700:
            return False, "%r: log directory mode is %o, want 700" % (cmd, mode)
    return True, ""


@special("special26-existing-log-file-fixed-to-600", ("r2", "r2:6.2"))
def sp_log_mode_fixed(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    for i, mode in enumerate((0o644, 0o666, 0o640)):
        home = _fresh_home(ctx, "logmode-%d" % i)
        os.makedirs(_hooks_dir(home))
        log = _log_path(home)
        with open(log, "w") as f:
            f.write("old line\n")
        os.chmod(log, mode)
        rc, _, _, _ = invoke(ctx, payload_for(ctx, 'rm -rf "$X"', "work"), home=home)
        if rc != 2:
            return False, "exit code %r" % (rc,)
        got = stat.S_IMODE(os.stat(log).st_mode)
        if got != 0o600:
            return False, "log created with mode %o keeps mode %o after a write, want 600" % (mode, got)
        with open(log, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        if len(lines) != 2 or lines[0] != "old line":
            return False, "existing log content was not preserved and appended to: %r" % (lines,)
    return True, ""


@special("special27-log-symlink-not-followed", ("r2", "r2:6.2"))
def sp_log_symlink(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    # an existing target file
    home = _fresh_home(ctx, "logsym-1")
    os.makedirs(_hooks_dir(home))
    decoy = os.path.join(home, "decoy.txt")
    with open(decoy, "w") as f:
        f.write("keep\n")
    os.symlink(decoy, _log_path(home))
    rc, out, err, _ = invoke(ctx, payload_for(ctx, 'rm -rf "$X"', "work"), home=home)
    why = check_deny_output(rc, out, err, "expansion")
    if why:
        return False, "symlinked log: " + why
    with open(decoy, encoding="utf-8") as f:
        if f.read() != "keep\n":
            return False, "the log write went through the symlink into the target file"
    # a dangling symlink must not be created through
    home = _fresh_home(ctx, "logsym-2")
    os.makedirs(_hooks_dir(home))
    missing = os.path.join(home, "not-created.txt")
    os.symlink(missing, _log_path(home))
    rc, out, err, _ = invoke(ctx, payload_for(ctx, "rm -rf ~", "work"), home=home)
    why = check_deny_output(rc, out, err, "tilde")
    if why:
        return False, "dangling symlinked log: " + why
    if os.path.lexists(missing):
        return False, "the log write created the symlink target"
    # a symlink to a directory
    home = _fresh_home(ctx, "logsym-3")
    os.makedirs(_hooks_dir(home))
    other = os.path.join(home, "otherdir")
    os.makedirs(other)
    os.symlink(other, _log_path(home))
    rc, out, err, _ = invoke(ctx, payload_for(ctx, "rm -rf /usr", "work"), home=home)
    why = check_deny_output(rc, out, err, "protected-path")
    if why:
        return False, "directory symlinked log: " + why
    return True, ""


# 7.2 speed
@special("special28-ordinary-commands-under-50ms-median", ("r2", "r2:7.2"))
def sp_perf_ordinary(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    script = "\n".join(["set -e", "cd /tmp/proj", "make clean", "npm ci", "npm test 2>&1 | tail -20",
                        'for f in a b c; do echo "$f"; done', "git status --short", "git add -A",
                        'git commit -m "x" && git push origin HEAD', "rm -rf dist build node_modules/.cache",
                        "d=$(mktemp -d) && echo hi > \"$d/x\" && rm -rf \"$d\"", "ls -la | head -20"])
    cmds = [["ls -la && git status --short | head -20", ctx.work], ["rm -rf /tmp/abc ./build node_modules", ctx.work],
            ["cd /tmp/proj && make clean && rm -rf dist", ctx.work], ["npm test 2>&1 | tail -5", ctx.work],
            [script, ctx.work], [DEFAULT_COMMIT, ctx.work], ["grep -rn 'rm -rf' docs | head", ctx.work]]
    home = _fresh_home(ctx, "perfhome")
    res, why = _run_perf(ctx, cmds, home)
    if res is None:
        return False, why
    slow = [(c[0][:40], "%.1fms" % (t * 1000)) for c, t in zip(cmds, res) if t >= 0.05]
    if slow:
        return False, "median of 20 judge() calls is not under 50ms: %r" % (slow,)
    return True, ""


def _run_perf(ctx, cmds, home):
    p = subprocess.Popen([sys.executable, "-c", PERF_SCRIPT, HOOK_PATH, json.dumps(cmds)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=ctx.env(home), cwd=ctx.work, start_new_session=True)
    try:
        out, err = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass
        p.communicate()
        return None, "timed out"
    if p.returncode != 0:
        return None, "python exit %r: %s" % (p.returncode, err.decode("utf-8", "replace")[-300:])
    return json.loads(out.decode("utf-8").strip().splitlines()[-1]), ""


@special("special29-big-heredoc-with-benign-substitutions-fast", ("r2", "r2:7.2"))
def sp_big_heredoc_subst(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    line = "生成于 $(date) 由 `hostname` 执行;rm -rf \"$HOME\" 是反例,不要运行\n"
    body = ""
    while len(body.encode("utf-8")) < 100 * 1024:
        body += line
    cmd = "cat > report.md <<EOF\n" + body + "EOF"
    rc, out, err, secs = invoke(ctx, payload_for(ctx, cmd, "work"))
    if rc != 0:
        return False, "exit code %r, want 0 (stderr=%r)" % (rc, err[:160])
    if secs >= 1.0:
        return False, "took %.2fs, want < 1s" % secs
    return True, ""


@special("special30-big-quoted-heredoc-fast", ("r2", "r2:7.2"))
def sp_big_heredoc_quoted(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    line = "文档正文 rm -rf $(pwd) `rm -rf ~` and it's fine\n"
    body = ""
    while len(body.encode("utf-8")) < 100 * 1024:
        body += line
    cmd = "cat > a.md <<'EOF'\n" + body + "EOF"
    rc, out, err, secs = invoke(ctx, payload_for(ctx, cmd, "work"))
    if rc != 0:
        return False, "exit code %r, want 0 (stderr=%r)" % (rc, err[:160])
    if secs >= 1.0:
        return False, "took %.2fs, want < 1s" % secs
    return True, ""


# 7.1 self checks of this table
P1_REPROS = [
    # #1 globs
    "rm -rf {REALHOME_PARENT}/{RN2}*", "rm -rf {REALHOME_PARENT}/{RN_Q}", "rm -rf /U*", "rm -rf /us*",
    "rm -rf {RL0}", "rm -rf {RL0B}", "rm -rf {REALHOME_PARENT}/{RN_BR}", "rm -rf {REALHOME}/../{RN2}*",
    "rm -rf {RN2}*", "cd {REALHOME_PARENT} && rm -rf {RN2}*", "rm -rf {REALHOME_PARENT}/{RN_PSTAR}",
    "rm -rf {REALHOME_PARENT}/{RN_PSTAR}/", "rm -rf {REALHOME_PARENT}/{RN_LASTBR}",
    "rm -rf {REALHOME_PARENT}/{RN_MID2}", "rm -rf {REALHOME_PARENT}/{RN3}*",
    # #2 / #15 cwd
    "(cd /tmp/x); rm -rf *", "(cd /tmp/x && make clean); rm -rf ./*", "X=$(cd /tmp/x; pwd); rm -rf *",
    "cd /tmp/does-not-exist; rm -rf *", "if [ -d /tmp/x ]; then cd /tmp/x; fi; rm -rf *",
    "(cd /tmp/x && make); rm -rf *", "cd /tmp/x || true; rm -rf ./*", "X=$(cd /tmp/a); rm -rf *",
    "cd /tmp/x || true; rm -rf .",
    # #3 / #14 assignments
    '(D=/tmp/x); rm -rf "$D"/*', 'if [ -d /tmp/x ]; then D=/tmp/x; fi; rm -rf "$D/"*',
    'D="$APP_HOME"; [ -d "$D" ] || D=$(mktemp -d); rm -rf "$D"',
    'D="$HOME"; test -n "$CI" && D=/tmp/ci; rm -rf "$D"', '[ -n "$HOME" ] || HOME=/tmp/x; rm -rf "$HOME"',
    'X=$HOME; (X=/tmp/safe); rm -rf "$X"', 'X=$HOME; : $(X=/tmp/safe); rm -rf "$X"',
    'X=$HOME; X=/tmp/safe | cat; rm -rf "$X"', 'X=$HOME; if false; then X=/tmp/a; fi; rm -rf "$X"',
    '[ -n "$CI" ] && X=/tmp/a; rm -rf "$X"/*', '( X=/tmp/a ); rm -rf "$X"/*', 'echo $(X=/tmp/a); rm -rf "$X"/*',
    'X=/tmp/a | cat; rm -rf "$X"/*', "d=$(mktemp -d); trap 'rm -rf \"$d\"' EXIT; d=$HOME",
    # #4 forms
    "function f { rm -rf {REALHOME}; }; f", "function f { rm -rf ~; }", 'function f { rm -rf "$X"; }; f',
    "function cleanup { rm -rf {REALHOME}; }; cleanup", "coproc rm -rf ~",
    'X=/tmp/x; printf -v X %s "$HOME"; rm -rf "$X"', 'declare -n X=HOME; rm -rf "$X"',
    'X=/tmp/a; printf -v X /; rm -rf "$X"',
    # #13 aliases
    "rm -rf '{BOOTVOL_REAL}{REALHOME}'", "rm -rf /System/Volumes", "find {BOOTVOL_REAL_ESC}{REALHOME} -delete",
    # #21 command-name expansion
    '$SUDO rm -rf "$HOME"', "$(which rm) -rf {REALHOME}", "${RM:-rm} -rf ~",
    # #22 unquoted heredoc substitutions
    "cat > a.md <<EOF\nstep: `rm -rf $HOME/x`\nEOF", "cat > a.md <<EOF\n$(rm -rf ~)\nEOF",
]


@special("special31-p1-reproductions-are-all-in-the-table", ("r2", "r2:7.1"))
def sp_p1_present(ctx):
    have = set(c["cmd"] for c in CASES)
    missing = [r for r in P1_REPROS if r not in have]
    if missing:
        return False, "%d first-round P1 reproductions are not in the table, first: %r" % (len(missing), missing[0])
    return True, ""


@special("special32-every-spec-item-has-enough-cases", ("r2", "r2:7.1"))
def sp_coverage(ctx):
    problems = []
    for item in R2_ITEMS:
        tagged = [e for e in SPECIALS if "r2:" + item in e["tags"]]
        counts = R2_COUNT.get(item, [0, 0])
        total = counts[0] + counts[1] + len(tagged)
        if total < 3:
            problems.append("%s has %d entries, want >= 3" % (item, total))
        if item not in SPECIAL_ITEMS and (counts[0] < 1 or counts[1] < 1):
            problems.append("%s needs both allow and deny cases (allow=%d deny=%d)" % (item, counts[0], counts[1]))
    if problems:
        return False, "; ".join(problems)
    return True, ""


@special("special33-every-rule-name-is-expected-in-revision-2", ("r2", "r2:7.1"))
def sp_rules_used(ctx):
    used = set()
    for c in CASES:
        if c["expect"] == "deny" and "r2" in c["tags"]:
            used.update((c["rule"],) if isinstance(c["rule"], str) else c["rule"])
    missing = [r for r in RULES if r not in used]
    if missing:
        return False, "no revision 2 deny case expects rule(s): %s" % ", ".join(missing)
    return True, ""


# self checks of the revision 3 block
R3_P1_STILL_DENIED = [
    # first-round P1 reproductions that must stay refused whatever revision 3 changes
    'D="$APP_HOME"; [ -d "$D" ] || D=$(mktemp -d); rm -rf "$D"',
    'X=$HOME; if false; then X=/tmp/a; fi; rm -rf "$X"',
    'if [ -d /tmp/x ]; then D=/tmp/x; fi; rm -rf "$D/"*',
    '[ -n "$CI" ] && X=/tmp/a; rm -rf "$X"/*',
    "cd /tmp/does-not-exist; rm -rf *",
    "(cd /tmp/x && make clean); rm -rf ./*",
    "X=$(cd /tmp/x; pwd); rm -rf *",
    "if [ -d /tmp/x ]; then cd /tmp/x; fi; rm -rf *",
    "cd /tmp/x || true; rm -rf ./*",
    "cd /tmp/x || true; rm -rf .",
    "(cd /tmp/x); rm -rf *",
    'D="$HOME"; test -n "$CI" && D=/tmp/ci; rm -rf "$D"',
    '[ -n "$HOME" ] || HOME=/tmp/x; rm -rf "$HOME"',
    'X=$HOME; (X=/tmp/safe); rm -rf "$X"',
    'X=$HOME; : $(X=/tmp/safe); rm -rf "$X"',
    'X=$HOME; X=/tmp/safe | cat; rm -rf "$X"',
    '(D=/tmp/x); rm -rf "$D"/*',
    '( X=/tmp/a ); rm -rf "$X"/*',
    'echo $(X=/tmp/a); rm -rf "$X"/*',
    'X=/tmp/a | cat; rm -rf "$X"/*',
    "d=$(mktemp -d); trap 'rm -rf \"$d\"' EXIT; d=$HOME",
]


@special("special34-every-revision-3-item-has-enough-cases", ("r3",))
def sp_r3_coverage(ctx):
    problems = []
    for item in R3_ITEMS:
        counts = R3_COUNT.get(item, [0, 0])
        if counts[0] + counts[1] < 3:
            problems.append("%s has %d entries, want >= 3" % (item, counts[0] + counts[1]))
        if counts[0] < 1 or counts[1] < 1:
            problems.append("%s needs both allow and deny cases (allow=%d deny=%d)" % (item, counts[0], counts[1]))
    if problems:
        return False, "; ".join(problems)
    return True, ""


@special("special35-first-round-p1-repros-are-never-expected-allowed", ("r3",))
def sp_r3_p1_denied(ctx):
    for cmd in R3_P1_STILL_DENIED:
        rows = [c for c in CASES if c["cmd"] == cmd]
        if not rows:
            return False, "first-round P1 reproduction missing from the table: %r" % (cmd,)
        bad = [c["id"] for c in rows if c["expect"] != "deny"]
        if bad:
            return False, "first-round P1 reproduction %r is expected to be allowed in %s" % (cmd, bad[0])
    return True, ""


# ---------------------------------------------------------------------------
# English mode (RM_GUARD_LANG=en): same rules, same rule= line, English text
# ---------------------------------------------------------------------------
EN_PHRASE = "Each Bash tool call starts a new shell"
EN_RULE_CASES = [
    # rule, deny command, deny cwd, allow command, allow cwd
    ("expansion", 'rm -rf "$X"', "work", 'rm "$f"', "work"),
    ("tilde", "rm -rf ~/x", "work", "rm -rf build~", "work"),
    ("protected-path", "rm --no-preserve-root -rf /", "work", "rm -rf {WORK}/sub", "work"),
    ("protected-glob", "bash -c 'cd ~ && rm -rf *'", "work", "rm -rf {WORK}/sub/*", "work"),
    ("unknown-cwd", "rm -rf .", "none", "rm -rf ./build", "work"),
    ("unparsable", 'rm -rf "$HOME', "work", 'echo "ok"', "work"),
]


def invoke_env(ctx, stdin_bytes, extra_env, argv=None, timeout=CASE_TIMEOUT):
    """Like invoke(), with extra environment variables (None value = unset) and optional argv."""
    env = ctx.env()
    for k, v in extra_env.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    p = subprocess.Popen(argv or ctx.argv(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, env=env, cwd=ctx.work, start_new_session=True)
    try:
        out, err = p.communicate(stdin_bytes, timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass
        p.communicate()
        return None, b"", b""
    finally:
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            p.wait()
    return p.returncode, out, err


def check_en_deny(rc, out, err, rule):
    """None when the deny output is the English form of `rule`, else a reason string."""
    if rc != 2:
        return "exit code %r, want 2 (stdout=%r stderr=%r)" % (rc, out[:120], err[:120])
    lines = [l for l in out.decode("utf-8", "replace").splitlines() if l.strip()]
    if len(lines) != 1:
        return "stdout should be one JSON line, got %d lines" % len(lines)
    try:
        hso = json.loads(lines[0])["hookSpecificOutput"]
    except Exception as e:
        return "stdout is not the expected JSON: %r" % (e,)
    if hso.get("permissionDecision") != "deny":
        return "permissionDecision is %r" % (hso.get("permissionDecision"),)
    reason = hso.get("permissionDecisionReason")
    if not isinstance(reason, str) or not reason:
        return "permissionDecisionReason missing"
    if not reason.split("\n", 1)[0].startswith("Blocked:"):
        return "first line does not start with Blocked: (%r)" % reason.split("\n", 1)[0][:60]
    if "已拒绝" in reason:
        return "English reason still contains Chinese text"
    found = RULE_LINE.findall(reason)
    if found != [rule]:
        return "rule= lines %r, want [%r]" % (found, rule)
    if rule == "expansion" and EN_PHRASE not in reason:
        return "expansion reason lacks the English sentence about new shells"
    if rule != "expansion" and EN_PHRASE in reason:
        return "non-expansion reason carries the expansion sentence"
    if reason.strip() not in err.decode("utf-8", "replace"):
        return "stderr does not carry the same reason"
    return None


def _en_rule_special(rule, deny_cmd, deny_cwd, allow_cmd, allow_cwd):
    def fn(ctx):
        miss = _need_hook()
        if miss:
            return False, miss
        env = {"RM_GUARD_LANG": "en"}
        rc, out, err = invoke_env(ctx, payload_for(ctx, ctx.subst(deny_cmd), deny_cwd), env)
        if rc is None:
            return False, "deny case timed out"
        why = check_en_deny(rc, out, err, rule)
        if why:
            return False, "deny: " + why
        rc, out, err = invoke_env(ctx, payload_for(ctx, ctx.subst(allow_cmd), allow_cwd), env)
        if rc is None:
            return False, "allow case timed out"
        if rc != 0 or out.strip():
            return False, "allow: exit %r stdout=%r stderr=%r" % (rc, out[:120], err[:120])
        return True, ""
    return fn


for _i, (_rule, _dc, _dw, _ac, _aw) in enumerate(EN_RULE_CASES):
    special("special50-en-%d-%s" % (_i + 1, _rule), ("en",))(_en_rule_special(_rule, _dc, _dw, _ac, _aw))


@special("special51-en-default-stays-chinese", ("en",))
def sp_en_default_zh(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    for label, env in (("unset", {"RM_GUARD_LANG": None}), ("zh", {"RM_GUARD_LANG": "zh"}),
                       ("EN-upper", {"RM_GUARD_LANG": "EN"}), ("empty", {"RM_GUARD_LANG": ""}),
                       ("other", {"RM_GUARD_LANG": "english"})):
        rc, out, err = invoke_env(ctx, payload_for(ctx, 'rm -rf "$X"', "work"), env)
        if rc is None:
            return False, "%s: timed out" % label
        why = check_deny_output(rc, out, err, "expansion")
        if why:
            return False, "%s: %s" % (label, why)
        if "Blocked:" in out.decode("utf-8", "replace"):
            return False, "%s: reason is English" % label
    return True, ""


def _hooks_json_command():
    """The PreToolUse command containing block-recursive-rm.py from hooks.json in the hooks directory,
    with ${CLAUDE_PLUGIN_ROOT} replaced by the parent of the hooks directory; None when absent."""
    path = os.path.join(HOOKS, "hooks.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for ent in data.get("hooks", {}).get("PreToolUse", []):
        for h in ent.get("hooks", []):
            c = h.get("command", "")
            if HOOK_NAME in c:
                return c.replace("${CLAUDE_PLUGIN_ROOT}", os.path.dirname(HOOKS))
    return None


@special("special52-en-hooks-json-command-as-written", ("en",))
def sp_en_hooks_json_command(ctx):
    miss = _need_hook()
    if miss:
        return False, miss
    # the command string as written in hooks.json, run through sh -c unchanged
    try:
        cmd = _hooks_json_command()
    except (OSError, ValueError) as e:
        return False, "cannot read hooks.json in %s: %r" % (HOOKS, e)
    if not cmd:
        return False, "no PreToolUse command with %s in %s/hooks.json" % (HOOK_NAME, HOOKS)
    rc, out, err = invoke_env(ctx, payload_for(ctx, 'rm -rf "$X"', "work"), {"RM_GUARD_LANG": None},
                              argv=["sh", "-c", cmd])
    if rc is None:
        return False, "timed out"
    if "RM_GUARD_LANG=en" in cmd:
        why = check_en_deny(rc, out, err, "expansion")
    else:
        why = check_deny_output(rc, out, err, "expansion")
    if why:
        return False, "hooks.json command: " + why
    # the hard-coded form with the variable in front of sh stays English; without it, Chinese
    cmd1 = 'RM_GUARD_LANG=en sh "%s" block-recursive-rm.py' % RUN_GUARD
    rc, out, err = invoke_env(ctx, payload_for(ctx, 'rm -rf "$X"', "work"), {"RM_GUARD_LANG": None},
                              argv=["sh", "-c", cmd1])
    why = check_en_deny(rc, out, err, "expansion") if rc is not None else "timed out"
    if why:
        return False, "hard-coded form: " + why
    cmd0 = 'sh "%s" block-recursive-rm.py' % RUN_GUARD
    rc, out, err = invoke_env(ctx, payload_for(ctx, 'rm -rf "$X"', "work"), {"RM_GUARD_LANG": None},
                              argv=["sh", "-c", cmd0])
    why = check_deny_output(rc, out, err, "expansion") if rc is not None else "timed out"
    if why:
        return False, "without the variable: " + why
    return True, ""


FALLBACK_SCRIPT = r"""
import importlib.util, io, sys
spec = importlib.util.spec_from_file_location("rmg", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
def boom(*a, **k):
    raise RuntimeError("forced")
m.build_reason = boom
sys.exit(m.main())
"""


def _fallback_special(lang):
    def fn(ctx):
        miss = _need_hook()
        if miss:
            return False, miss
        env = {"RM_GUARD_LANG": "en" if lang == "en" else None}
        rc, out, err = invoke_env(ctx, payload_for(ctx, 'rm -rf "$X"', "work"), env,
                                  argv=[sys.executable, "-c", FALLBACK_SCRIPT, HOOK_PATH])
        if rc is None:
            return False, "timed out"
        if rc != 2:
            return False, "exit code %r, want 2" % (rc,)
        lines = [l for l in out.decode("utf-8", "replace").splitlines() if l.strip()]
        if len(lines) != 1:
            return False, "stdout should be one JSON line, got %d" % len(lines)
        try:
            reason = json.loads(lines[0])["hookSpecificOutput"]["permissionDecisionReason"]
        except Exception as e:
            return False, "stdout is not the expected JSON: %r" % (e,)
        prefix = "Blocked:" if lang == "en" else "已拒绝:"
        if not reason.split("\n", 1)[0].startswith(prefix):
            return False, "first line %r does not start with %s" % (reason.split("\n", 1)[0][:60], prefix)
        if RULE_LINE.findall(reason) != ["expansion"]:
            return False, "rule= lines %r, want ['expansion']" % (RULE_LINE.findall(reason),)
        if reason.strip() not in err.decode("utf-8", "replace"):
            return False, "stderr does not carry the same reason"
        return True, ""
    return fn


special("special53-fallback-reason-en", ("en",))(_fallback_special("en"))
special("special54-fallback-reason-zh", ("en",))(_fallback_special("zh"))


# ---------------------------------------------------------------------------
def all_entries():
    entries = [("case", c) for c in CASES] + [("special", s) for s in SPECIALS]
    return entries


def tags_of(kind, obj):
    return obj["tags"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--direct", action="store_true",
                    help="run python3 <hook> directly instead of via run-guard.sh")
    ap.add_argument("--only", default="", help="only cases whose id starts with this prefix")
    ap.add_argument("--jobs", type=int, default=4, help="parallel subprocesses (capped at %d)" % MAX_JOBS)
    ap.add_argument("--list", action="store_true", help="print case ids and per-category counts, then exit")
    args = ap.parse_args()

    entries = [e for e in all_entries() if e[1]["id"].startswith(args.only)]

    if args.list:
        cats = {}
        for kind, obj in entries:
            print(obj["id"])
            for t in set(obj["tags"]):
                c = cats.setdefault(t, [0, 0, 0])
                c[0] += 1
                if kind == "case":
                    c[1 if obj["expect"] == "allow" else 2] += 1
        for t in sorted(cats):
            print("CATEGORY %s total=%d allow=%d deny=%d" % (t, cats[t][0], cats[t][1], cats[t][2]))
        print("TOTAL %d" % len(entries))
        return 0

    jobs = max(1, min(args.jobs, MAX_JOBS))
    results = {}
    with tempfile.TemporaryDirectory(prefix="rm-guard-cases-") as base:
        ctx = Ctx(base, args.direct)
        def run_entry(entry):
            kind, obj = entry
            if kind == "case":
                return run_case(obj, ctx)
            try:
                return obj["fn"](ctx)
            except Exception as e:
                return False, "runner error: %r" % (e,)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
                futs = {ex.submit(run_entry, e): e for e in entries}
                for fut in concurrent.futures.as_completed(futs):
                    results[futs[fut][1]["id"]] = fut.result()
        finally:
            ctx.cleanup_links()

    passed = failed = skipped = 0
    for kind, obj in entries:
        ok, why = results[obj["id"]]
        if ok == "skip":
            skipped += 1
            print("SKIP %s  %s" % (obj["id"], why))
        elif ok:
            passed += 1
            print("PASS %s" % obj["id"])
        else:
            failed += 1
            print("FAIL %s  %s" % (obj["id"], why))
    print("SUMMARY %d %d %d %d" % (len(entries), passed, failed, skipped))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
