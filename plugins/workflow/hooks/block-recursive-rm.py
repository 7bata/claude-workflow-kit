#!/usr/bin/env python3
"""PreToolUse hook: reject recursive deletes whose target cannot be determined
before the command runs, or that land on a home / system directory.

Reads the hook JSON on stdin ({"tool_input": {"command": ...}, "cwd": ...}).
On a rejection it exits 2, prints one JSON line with permissionDecision "deny"
on stdout and the same reason on stderr. Otherwise it exits 0 with no output.

What is judged:
  * `rm` with a recursive option (all calling forms and wrapper commands),
    `find ... -delete`, `find ... -exec rm`;
  * the same rules applied recursively to `sh -c` strings, `eval`, command and
    process substitutions, shell / ssh heredoc and here-string bodies, text piped
    into a shell, `ssh host '...'`, `trap '...'`, `xargs sh -c`, `find -exec sh -c`.
Variables and the working directory are tracked as sets of possible values: an assignment or cd
that may not run (right of && / ||, inside a branch or loop body, before a ; that follows an
&& chain) adds its value to the old set, a certain one replaces it, and a relative target is
judged once for every possible working directory. A name that was never assigned reads as
unknown; one that is only assigned conditionally starts as empty unless it was read first
(or is a usual environment name).
Rejection rules, in the order they are checked for each target:
  expansion, tilde, protected-path, protected-glob, unknown-cwd, unparsable.

The judgement is a pure function (`judge`): it reads no stdin, writes no log and
runs no command (it only resolves symbolic links of literal paths). Only the
standard library is used (python 3.9 compatible).

Language: the rejection reason is Chinese by default; when the environment variable
RM_GUARD_LANG is exactly "en" it is English (set by the hooks.json command of the
English plugin). The "rule=" line and the log format are the same in both.
"""
import datetime
import fnmatch
import json
import os
import re
import sys

try:
    import pwd
except ImportError:  # pragma: no cover - non-unix
    pwd = None

LOG_PATH = os.path.expanduser("~/.claude/hooks/rm-guard.log")
MAX_DEPTH = 8
MAX_BRACE_RESULTS = 256
MAX_LEX_NEST = 40
MAX_BRACE_TEXT = 4000
MAX_PARALLEL_ARGS = 64
DARWIN = sys.platform == "darwin"

RULES = ("expansion", "tilde", "protected-path", "protected-glob", "unknown-cwd", "unparsable")

SYSTEM_DIRS = frozenset([
    "/System", "/System/Volumes", "/Library", "/Applications", "/Users", "/Volumes", "/usr",
    "/usr/local", "/bin", "/sbin", "/etc", "/var", "/tmp", "/opt", "/opt/homebrew", "/private",
    "/dev", "/cores", "/home", "/root", "/boot", "/lib", "/lib64", "/proc", "/sys", "/srv",
    "/mnt", "/media", "/snap", "/nix",
])
ENV_NAMES = frozenset([
    "HOME", "TMPDIR", "TMP", "TEMP", "PWD", "OLDPWD", "USER", "LOGNAME", "SHELL", "PATH", "TERM",
    "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_RUNTIME_DIR",
    "CLAUDE_PROJECT_DIR", "CLAUDE_CONFIG_DIR", "GOPATH", "GOROOT", "GOCACHE", "CARGO_HOME",
    "RUSTUP_HOME", "NVM_DIR", "PNPM_HOME", "ZDOTDIR", "ZSH", "HISTFILE",
])
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
REMOTE_FIND_DIRS = frozenset(["/Users", "/home", "/root"])

SHELLS = frozenset(["sh", "bash", "zsh", "dash", "ksh", "ash", "fish"])
# words that may stand in front of a command inside a compound command
KEYWORDS = frozenset(["if", "then", "else", "elif", "fi", "while", "until", "do", "done", "case",
                      "esac", "for", "select", "!", "{", "}"])
# lead words after which a new command (case / group) may still start
LEAD_KW = frozenset(["then", "do", "else", "elif", "if", "while", "until", "!"])
ASSIGN_BUILTINS = frozenset(["export", "local", "declare", "readonly", "typeset"])
CLEAR_BUILTINS = frozenset(["unset"])
QD = 1   # quoted (double quotes, expansion text)
QS = 2   # literal (single quotes, backslash escape)


class Unparsable(Exception):
    pass


class Hit(Exception):
    def __init__(self, rule, target):
        Exception.__init__(self, rule)
        self.rule = rule
        self.target = target


# ---------------------------------------------------------------------------
# lexer: splits shell text into commands (words, separators, groups)
# ---------------------------------------------------------------------------
class Word(object):
    __slots__ = ("raw", "text", "q", "expands", "subs", "refs")

    def __init__(self, raw, text, q, expands, subs, refs=()):
        self.raw = raw
        self.text = text      # value with quotes / escapes removed ($... kept as written)
        self.q = q            # per char of text: 0 unquoted, QD quoted, QS literal
        self.expands = expands
        self.subs = subs      # inner texts of $(...), `...`, <(...), >(...)
        self.refs = dict(refs)   # text index of each "$" that starts an expansion -> inside double quotes

    def plain(self):
        return not self.expands and not any(self.q)


class Heredoc(object):
    __slots__ = ("delim", "quoted", "strip", "body")

    def __init__(self, delim, quoted, strip):
        self.delim = delim
        self.quoted = quoted
        self.strip = strip
        self.body = ""


class Group(object):
    __slots__ = ("kind", "items")

    def __init__(self, kind, items):
        self.kind = kind      # "sub" ( ... ) or "brace" { ...; }
        self.items = items


class Mark(object):
    __slots__ = ("kind",)

    def __init__(self, kind):
        self.kind = kind      # "case_open" | "case_close"


class Cmd(object):
    __slots__ = ("words", "extra", "heredocs", "herestrings", "sep", "group")

    def __init__(self):
        self.words = []
        self.extra = []         # redirect target words (only their substitutions matter)
        self.heredocs = []
        self.herestrings = []
        self.sep = None         # separator that follows the command
        self.group = None


_DQ_RUN = re.compile(r'[^"\\$`]+')
_NAME_ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")
_FUNC_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.:-]*\Z")


def _skip_squote(s, j):
    k = s.find("'", j + 1)
    if k < 0:
        raise Unparsable("single quote")
    return k + 1


def _skip_ansi(s, j):
    """j at the opening quote of $'...'; returns index after the closing quote."""
    n = len(s)
    k = j + 1
    while k < n:
        if s[k] == "\\":
            k += 2
            continue
        if s[k] == "'":
            return k + 1
        k += 1
    raise Unparsable("ANSI-C quote")


def _skip_backtick(s, j):
    n = len(s)
    k = j + 1
    while k < n:
        if s[k] == "\\":
            k += 2
            continue
        if s[k] == "`":
            return k + 1
        k += 1
    raise Unparsable("backtick")


def _skip_dq(s, j):
    """j at an opening double quote; returns index after the closing one."""
    n = len(s)
    k = j + 1
    while k < n:
        c = s[k]
        if c == "\\":
            k += 2
        elif c == '"':
            return k + 1
        elif c == "$" and k + 1 < n and s[k + 1] == "(":
            k = _match_paren(s, k + 2) + 1
        elif c == "$" and k + 1 < n and s[k + 1] == "{":
            k = _match_brace(s, k + 2) + 1
        elif c == "`":
            k = _skip_backtick(s, k)
        else:
            k += 1
    raise Unparsable("double quote")


def _match_paren(s, i):
    """i is the index just after '(' ; returns the index of the matching ')'.
    The text in between is read by a nested lexer, so quotes, comments and heredocs
    inside it are understood."""
    if _Lexer.nest >= MAX_LEX_NEST:
        raise Unparsable("nesting too deep")
    _Lexer.nest += 1
    try:
        lx = _Lexer(s, i, True)
        lx.run()
        return lx.end
    finally:
        _Lexer.nest -= 1


def _match_brace(s, i):
    """i is the index just after '${' ; returns the index of the matching '}'."""
    n = len(s)
    depth = 1
    j = i
    while j < n:
        c = s[j]
        if c == "'":
            j = _skip_squote(s, j)
        elif c == '"':
            j = _skip_dq(s, j)
        elif c == "\\":
            j += 2
        elif c == "`":
            j = _skip_backtick(s, j)
        elif c == "$" and j + 1 < n and s[j + 1] == "{":
            depth += 1
            j += 2
        elif c == "$" and j + 1 < n and s[j + 1] == "(":
            j = _match_paren(s, j + 2) + 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
            j += 1
        else:
            j += 1
    raise Unparsable("brace")


class _Lexer(object):
    nest = 0

    def __init__(self, src, pos=0, paren=False):
        self.s = src
        self.pos = pos
        self.paren = paren          # True: stop at the unmatched ')' (substitution body)
        self.end = None
        self.items = []
        self.cur = Cmd()
        self.stack = []             # open groups: (kind, holder command, saved items)
        self.case = []              # per open case statement: "wait_in" | "pat" | "body"
        self.pending_redir = None   # None | "redir" | "heredoc" | "heredoc-" | "herestring"
        self.pending_hd = []
        self._reset_word()

    def _reset_word(self):
        self.inword = False
        self.start = 0
        self.text = []
        self.q = []
        self.subs = []
        self.refs = []
        self.expands = False

    # -- word building -----------------------------------------------------
    def begin(self, i):
        if not self.inword:
            self.inword = True
            self.start = i

    def add(self, ch, quoted):
        self.text.append(ch)
        self.q.append(quoted)

    def add_str(self, st, quoted):
        self.text.extend(st)
        self.q.extend([quoted] * len(st))

    def _lead_only(self):
        c = self.cur
        if c.extra or c.heredocs or c.group is not None:
            return False
        return all(w.plain() and w.text in LEAD_KW for w in c.words)

    def _is_header(self):
        c = self.cur
        w = c.words
        if not w or c.extra or c.heredocs or c.group is not None:
            return False
        f = w[0]
        if not f.plain():
            return False
        if f.text == "function":
            return len(w) == 2 and w[1].plain()
        if f.text == "coproc":
            return len(w) <= 2
        return False

    def flush(self, i):
        if not self.inword:
            return
        word = Word(self.s[self.start:i], "".join(self.text), self.q, self.expands, self.subs, self.refs)
        self._reset_word()
        if self.pending_redir is not None:
            kind = self.pending_redir
            self.pending_redir = None
            if kind.startswith("heredoc"):
                quoted = any(ch in word.raw for ch in "'\"\\")
                hd = Heredoc(word.text, quoted, kind == "heredoc-")
                self.cur.heredocs.append(hd)
                self.pending_hd.append(hd)
            else:
                self.cur.extra.append(word)
                if kind == "herestring":
                    self.cur.herestrings.append(word)
            return
        cur = self.cur
        plain = word.plain()
        if plain:
            t = word.text
            if t == "{" and (not cur.words and not cur.extra and not cur.heredocs and cur.group is None
                             or self._lead_only() or self._is_header()):
                self.open_group("brace")
                return
            if t == "}" and not cur.words and not cur.extra and self.stack and self.stack[-1][0] == "brace":
                self.close_group()
                return
            if t == "case" and self._lead_only():
                self.case.append("wait_in")
            elif t == "esac" and self._lead_only() and self.case and self.case[-1] in ("pat", "body"):
                self.case.pop()
            elif t == "in" and self.case and self.case[-1] == "wait_in":
                cur.words.append(word)
                self.case[-1] = "pat"
                self.end_cmd(";")
                return
        cur.words.append(word)

    def end_cmd(self, sep=None):
        c = self.cur
        if c.words or c.extra or c.heredocs or c.group is not None:
            c.sep = sep
            self.items.append(c)
        self.cur = Cmd()
        self.pending_redir = None

    def open_group(self, kind):
        if len(self.stack) >= MAX_LEX_NEST:
            raise Unparsable("groups nested too deep")
        self.stack.append((kind, self.cur, self.items))
        self.items = []
        self.cur = Cmd()
        self.pending_redir = None

    def close_group(self):
        kind, holder, saved = self.stack.pop()
        self.end_cmd(None)
        inner = self.items
        self.items = saved
        holder.group = Group(kind, inner)
        self.cur = holder
        self.pending_redir = None

    # -- pieces ------------------------------------------------------------
    def read_heredocs(self, pos):
        s = self.s
        n = len(s)
        for hd in self.pending_hd:
            j = pos
            body_start = pos
            body = None
            while True:
                if j >= n:
                    body = s[body_start:n]
                    j = n
                    break
                k = s.find("\n", j)
                line_end = n if k < 0 else k
                line = s[j:line_end]
                if (line.lstrip("\t") if hd.strip else line) == hd.delim:
                    body = s[body_start:j]
                    j = n if k < 0 else k + 1
                    break
                if k < 0:
                    body = s[body_start:n]
                    j = n
                    break
                j = k + 1
            hd.body = body
            pos = j
        self.pending_hd = []
        return pos

    def dollar(self, i, quoted):
        s = self.s
        n = len(s)
        self.refs.append((len(self.text), quoted))
        nxt = s[i + 1] if i + 1 < n else ""
        if nxt == "(":
            j = _match_paren(s, i + 2)
            self.subs.append(s[i + 2:j])
            self.expands = True
            self.add_str(s[i:j + 1], QD)
            return j + 1
        if nxt == "{":
            j = _match_brace(s, i + 2)
            self.expands = True
            self.add_str(s[i:j + 1], QD)
            return j + 1
        if nxt == "'" and not quoted:
            j = _skip_ansi(s, i + 1)
            self.expands = True
            self.add_str(s[i:j], QD)
            return j
        if nxt == '"' and not quoted:
            self.expands = True
            return self.dq(i + 1)
        self.expands = True
        self.add("$", QD)
        return i + 1

    def backtick(self, i):
        s = self.s
        j = _skip_backtick(s, i)
        inner = s[i + 1:j - 1]
        inner = re.sub(r"\\([\\`$])", r"\1", inner)
        self.subs.append(inner)
        self.expands = True
        self.add_str(s[i:j], QD)
        return j

    def dq(self, i):
        s = self.s
        n = len(s)
        self.begin(i)
        j = i + 1
        while True:
            if j >= n:
                raise Unparsable("double quote")
            m = _DQ_RUN.match(s, j)
            if m:
                self.add_str(m.group(0), QD)
                j = m.end()
                continue
            ch = s[j]
            if ch == '"':
                return j + 1
            if ch == "\\":
                if j + 1 >= n:
                    raise Unparsable("double quote")
                d = s[j + 1]
                if d in '$`"\\':
                    self.add(d, QS)
                    j += 2
                elif d == "\n":
                    j += 2
                else:
                    self.add("\\", QD)
                    j += 1
            elif ch == "$":
                j = self.dollar(j, True)
            else:  # backtick
                j = self.backtick(j)

    def redirect(self, i):
        s = self.s
        n = len(s)
        c = s[i]
        # fd number glued in front of the operator
        if self.inword and not any(self.q) and "".join(self.text).isdigit():
            self._reset_word()
        else:
            self.flush(i)
        j = i + 1
        kind = "redir"
        if c == "&":  # &> or &>>
            j = i + 2
            if j < n and s[j] == ">":
                j += 1
        elif c == "<" and j < n and s[j] == "<":
            j += 1
            if j < n and s[j] == "<":
                j += 1
                kind = "herestring"
            else:
                kind = "heredoc"
                if j < n and s[j] == "-":
                    kind = "heredoc-"
                    j += 1
        elif c == ">" and j < n and s[j] in ">|":
            j += 1
        elif j < n and s[j] == "&":
            j += 1
        elif c == "<" and j < n and s[j] == ">":
            j += 1
        self.pending_redir = kind
        return j

    def _peek(self, i):
        s = self.s
        n = len(s)
        while i < n and s[i] in " \t":
            i += 1
        return i

    def _peek_any(self, i):
        s = self.s
        n = len(s)
        while i < n and s[i] in " \t\r\n":
            i += 1
        return i

    def open_paren(self, i):
        """'(' at index i that is not part of $( <( >( ; returns the next index."""
        s = self.s
        n = len(s)
        if self.case and self.case[-1] == "pat" and not self.cur.words and not self.inword:
            return i + 1                      # optional '(' in front of a case pattern
        if self.inword and i > self.start and s[i - 1] in "@!?*+":
            # extglob group such as @(a|b): part of the word
            j = _match_paren(s, i + 1)
            self.add_str(s[i:j + 1], 0)
            return j + 1
        self.flush(i)
        k = self._peek(i + 1)
        if self._is_header():
            if k < n and s[k] == ")":
                return k + 1                  # function f() ...
            self.open_group("sub")
            return i + 1
        if k < n and s[k] == ")" and len(self.cur.words) == 1 and self.cur.words[0].plain() \
                and self.cur.words[0].text not in KEYWORDS and _FUNC_NAME.match(self.cur.words[0].text):
            name = self.cur.words[0]
            self.cur.words = [Word("function", "function", [0] * 8, False, [], ()), name]
            return k + 1                      # name() ...
        if self.cur.words and not self._lead_only():
            self.end_cmd("")
        self.open_group("sub")
        return i + 1

    def run(self):
        s = self.s
        n = len(s)
        i = self.pos
        while i < n:
            c = s[i]
            if c == " " or c == "\t" or c == "\r":
                self.flush(i)
                i += 1
            elif c == "\n":
                self.flush(i)
                if self._is_header():
                    k = self._peek_any(i + 1)
                    if k < n and s[k] in "{(":
                        i += 1
                        continue
                self.end_cmd("\n")
                i += 1
                if self.pending_hd:
                    i = self.read_heredocs(i)
            elif c == "\\":
                if i + 1 < n:
                    d = s[i + 1]
                    if d == "\n":
                        i += 2
                        continue
                    self.begin(i)
                    self.add(d, QS)
                    i += 2
                else:
                    i += 1
            elif c == "'":
                self.begin(i)
                j = s.find("'", i + 1)
                if j < 0:
                    raise Unparsable("single quote")
                self.add_str(s[i + 1:j], QS)
                i = j + 1
            elif c == '"':
                i = self.dq(i)
            elif c == "`":
                self.begin(i)
                i = self.backtick(i)
            elif c == "$":
                self.begin(i)
                i = self.dollar(i, False)
            elif c == "#" and not self.inword:
                j = s.find("\n", i)
                i = n if j < 0 else j
            elif c in "<>" and i + 1 < n and s[i + 1] == "(":
                self.begin(i)
                j = _match_paren(s, i + 2)
                self.subs.append(s[i + 2:j])
                self.expands = True
                self.add_str(s[i:j + 1], QD)
                i = j + 1
            elif c in "<>":
                i = self.redirect(i)
            elif c == "&" and i + 1 < n and s[i + 1] == ">":
                i = self.redirect(i)
            elif c == "(":
                i = self.open_paren(i)
            elif c == ")":
                self.flush(i)
                if self.case and self.case[-1] == "pat":
                    self.cur = Cmd()
                    self.pending_redir = None
                    self.case[-1] = "body"
                    self.items.append(Mark("case_open"))
                elif self.stack:
                    self.close_group()
                elif self.paren:
                    self.end_cmd(None)
                    self.end = i
                    return self.items
                else:
                    self.end_cmd(None)
                i += 1
            elif c == ";":
                self.flush(i)
                if s.startswith(";;&", i):
                    sep, i = ";;&", i + 3
                elif s.startswith(";;", i):
                    sep, i = ";;", i + 2
                elif s.startswith(";&", i):
                    sep, i = ";&", i + 2
                else:
                    sep, i = ";", i + 1
                self.end_cmd(sep)
                if sep != ";":
                    self.items.append(Mark("case_close"))
                    if self.case and self.case[-1] == "body":
                        self.case[-1] = "pat"
            elif c == "|":
                self.flush(i)
                if self.case and self.case[-1] == "pat":
                    i += 1
                elif s.startswith("||", i):
                    self.end_cmd("||")
                    i += 2
                elif s.startswith("|&", i):
                    self.end_cmd("|")
                    i += 2
                else:
                    self.end_cmd("|")
                    i += 1
            elif c == "&":
                self.flush(i)
                if s.startswith("&&", i):
                    self.end_cmd("&&")
                    i += 2
                else:
                    self.end_cmd("&")
                    i += 1
            else:
                self.begin(i)
                self.add(c, 0)
                i += 1
        if self.paren:
            raise Unparsable("parenthesis")
        self.flush(n)
        self.end_cmd(None)
        if self.stack:
            raise Unparsable("unclosed group")
        return self.items


def lex(src):
    return _Lexer(src).run()


_HD_SCAN = re.compile(r"\\.|\$\(|`", re.S)


def heredoc_substitutions(body):
    """Texts of $( ) and `` substitutions in an unquoted heredoc body (the shell runs them)."""
    out = []
    i = 0
    while True:
        m = _HD_SCAN.search(body, i)
        if not m:
            break
        t = m.group(0)
        if t == "$(":
            j = _match_paren(body, m.end())
            out.append(body[m.end():j])
            i = j + 1
        elif t == "`":
            j = _skip_backtick(body, m.start())
            out.append(re.sub(r"\\([\\`$])", r"\1", body[m.start() + 1:j - 1]))
            i = j
        else:
            i = m.end()
    return out


# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
def norm_plain(p):
    parts = []
    for c in p.split("/"):
        if c == "" or c == ".":
            continue
        if c == "..":
            if parts:
                parts.pop()
            continue
        parts.append(c)
    return "/" + "/".join(parts)


def _key(p):
    return p.lower() if DARWIN else p


def _key_levels(levels):
    if DARWIN:
        return tuple(x.lower() for x in levels)
    return tuple(levels)


def get_homes():
    out = []
    env_home = os.environ.get("HOME")
    if env_home and env_home.startswith("/"):
        out.append(norm_plain(env_home))
    if pwd is not None:
        try:
            pw_home = pwd.getpwuid(os.getuid()).pw_dir
        except Exception:
            pw_home = ""
        if pw_home and pw_home.startswith("/"):
            h = norm_plain(pw_home)
            if h not in out:
                out.append(h)
    return out


def _lv(path):
    return tuple(c for c in path.split("/") if c)


def _spell(paths):
    """All spellings of the given protected paths (tuples of levels): the private/ and
    System/Volumes/Data aliases. Returns (set of keys, dict depth -> list of keys)."""
    out = set()
    for p in paths:
        variants = [p]
        if p and p[0] in ("tmp", "var", "etc"):
            variants.append(("private",) + p)
        for v in variants:
            out.add(v)
            out.add(("System", "Volumes", "Data") + v)
    keys = set(_key_levels(p) for p in out)
    by_depth = {}
    for k in keys:
        by_depth.setdefault(len(k), []).append(k)
    return keys, by_depth


_SPELL_CACHE = {}


def get_spellings(homes):
    ck = tuple(homes)
    got = _SPELL_CACHE.get(ck)
    if got is not None:
        return got
    chain = set([()])
    for h in homes:
        lv = _lv(h)
        for k in range(len(lv) + 1):
            chain.add(lv[:k])
    system = set(_lv(p) for p in SYSTEM_DIRS)
    remote_find = set(_lv(p) for p in REMOTE_FIND_DIRS)
    got = {
        "rm": _spell(chain | system),
        "rm_remote": _spell(set([()]) | system),
        "find": _spell(chain),
        "find_remote": _spell(set([()]) | remote_find),
    }
    _SPELL_CACHE[ck] = got
    return got


class Level(object):
    __slots__ = ("lit", "key", "pat", "glob", "only")

    def __init__(self, lit, pat=None, glob=False, only=False):
        self.lit = lit
        self.key = lit.lower() if DARWIN else lit
        self.pat = pat
        self.glob = glob
        self.only = only


def make_level(chars, qs):
    lit = "".join(chars)
    n = len(chars)
    has = False
    core = []
    pat = []
    for k, ch in enumerate(chars):
        quoted = qs[k]
        if not quoted and ch in "*?":
            has = True
            core.append(ch)
            pat.append(ch)
        elif not quoted and ch == "[":
            if any((not qs[m]) and chars[m] == "]" for m in range(k + 1, n)):
                has = True
                core.append("[")
                pat.append("[")
            else:
                core.append("x")
                pat.append("[[]")
        elif ch in "*?[":
            core.append("x")
            pat.append("[" + ch + "]")
        elif not quoted and ch in ".]":
            core.append(ch)
            pat.append(ch)
        else:
            core.append("x")
            pat.append(ch)
    if not has:
        return Level(lit)
    p = "".join(pat).replace("[^", "[!")
    if DARWIN:
        p = p.lower()
    stripped = re.sub(r"\[[^\]]*\]", "*", "".join(core))
    only = all(ch in "*?." for ch in stripped)
    return Level(lit, p, True, only)


def split_levels(text, q):
    levels = []
    chars = []
    qs = []
    for k, ch in enumerate(text):
        if ch == "/":
            levels.append(make_level(chars, qs))
            chars = []
            qs = []
        else:
            chars.append(ch)
            qs.append(q[k])
    levels.append(make_level(chars, qs))
    return levels


def normalize_levels(levels):
    out = []
    for lv in levels:
        if not lv.glob:
            if lv.lit == "" or lv.lit == ".":
                continue
            if lv.lit == "..":
                if out:
                    out.pop()
                continue
        out.append(lv)
    return out


def _match_levels(levels, spelled):
    if len(levels) != len(spelled):
        return False
    for lv, s in zip(levels, spelled):
        if lv.glob:
            if not fnmatch.fnmatchcase(s, lv.pat):
                return False
        elif lv.key != s:
            return False
    return True


def _real_levels(names, trailing):
    """Resolve symbolic links in all but the last component (the last one too when the
    target ends in / or /.). Returns a list of names, or None when nothing changed."""
    p = "/" + "/".join(names)
    try:
        if trailing or not names:
            rp = os.path.realpath(p)
        else:
            rp = os.path.join(os.path.realpath("/" + "/".join(names[:-1])), names[-1])
    except (OSError, ValueError):
        return None
    if rp == p:
        return None
    return [c for c in rp.split("/") if c]


def literal_hit(names, trailing, spelled):
    if _key_levels(names) in spelled:
        return True
    alt = _real_levels(names, trailing)
    return alt is not None and _key_levels(alt) in spelled


def glob_hit(levels, by_depth):
    for sp in by_depth.get(len(levels), ()):
        if _match_levels(levels, sp):
            return True
    for g, lv in enumerate(levels):
        if lv.glob and lv.only:
            for sp in by_depth.get(g, ()):
                if _match_levels(levels[:g], sp):
                    return True
    return False


def glob_protected(levels, by_depth):
    if glob_hit(levels, by_depth):
        return True
    first = 0
    while first < len(levels) and not levels[first].glob:
        first += 1
    if first:
        alt = _real_levels([lv.lit for lv in levels[:first]], True)
        if alt is not None:
            alt_levels = [Level(c) for c in alt] + levels[first:]
            return glob_hit(alt_levels, by_depth)
    return False


# ---------------------------------------------------------------------------
# braces
# ---------------------------------------------------------------------------
_SEQ = re.compile(r"(-?\d+|[A-Za-z])\.\.(-?\d+|[A-Za-z])(?:\.\.(-?\d+))?\Z")


def _brace_sequence(body):
    m = _SEQ.match(body)
    if not m:
        return None
    a, b, st = m.group(1), m.group(2), m.group(3)
    step = abs(int(st)) if st else 1
    if step == 0:
        step = 1
    if a.lstrip("-").isdigit() and b.lstrip("-").isdigit():
        x, y = int(a), int(b)
        width = 0
        if (len(a.lstrip("-")) > 1 and a.lstrip("-").startswith("0")) or \
                (len(b.lstrip("-")) > 1 and b.lstrip("-").startswith("0")):
            width = max(len(a), len(b))
        vals = []
        cur = x
        if x <= y:
            while cur <= y:
                vals.append(cur)
                cur += step
                if len(vals) > MAX_BRACE_RESULTS:
                    break
        else:
            while cur >= y:
                vals.append(cur)
                cur -= step
                if len(vals) > MAX_BRACE_RESULTS:
                    break
        return [str(v).zfill(width) if width else str(v) for v in vals]
    if len(a) == 1 and len(b) == 1 and a.isalpha() and b.isalpha():
        x, y = ord(a), ord(b)
        rng = range(x, y + 1, step) if x <= y else range(x, y - 1, -step)
        return [chr(v) for v in rng]
    return None


def brace_expand(text, q):
    """Expand unquoted {a,b} lists and {a..b} sequences. Returns a list of (text, q)
    pairs; raises Hit('unparsable') when more than MAX_BRACE_RESULTS come out."""
    if len(text) > MAX_BRACE_TEXT and "{" in text:
        raise Hit("unparsable", text[:200])
    out = _brace(text, q)
    return out


def _brace(text, q):
    n = len(text)
    i = 0
    while i < n:
        if text[i] == "{" and not q[i]:
            depth = 0
            commas = []
            j = i
            while j < n:
                if not q[j]:
                    ch = text[j]
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    elif ch == "," and depth == 1:
                        commas.append(j)
                j += 1
            if j < n and commas:
                bounds = [i] + commas + [j]
                results = []
                for a, b in zip(bounds[:-1], bounds[1:]):
                    alt_t = text[:i] + text[a + 1:b] + text[j + 1:]
                    alt_q = q[:i] + q[a + 1:b] + q[j + 1:]
                    results.extend(_brace(alt_t, alt_q))
                    if len(results) > MAX_BRACE_RESULTS:
                        raise Hit("unparsable", text[:200])
                return results
            if j < n and not commas and not any(q[i + 1:j]):
                vals = _brace_sequence(text[i + 1:j])
                if vals is not None:
                    if len(vals) > MAX_BRACE_RESULTS:
                        raise Hit("unparsable", text[:200])
                    results = []
                    for v in vals:
                        alt_t = text[:i] + v + text[j + 1:]
                        alt_q = q[:i] + [0] * len(v) + q[j + 1:]
                        results.extend(_brace(alt_t, alt_q))
                        if len(results) > MAX_BRACE_RESULTS:
                            raise Hit("unparsable", text[:200])
                    return results
        i += 1
    return [(text, q)]


# ---------------------------------------------------------------------------
# text fallback (unparsable commands)
# ---------------------------------------------------------------------------
_XARGS_LONG = ("--max-args", "--max-procs", "--delimiter", "--arg-file", "--max-lines",
               "--max-chars", "--eof", "--process-slot-var")
_PARALLEL_LONG = ("--jobs", "--max-args", "--sshlogin", "--arg-file", "--delimiter",
                  "--colsep", "--results", "--max-replace-args", "--replace")
_SUDO_LONG = ("--close-from", "--chdir", "--group", "--host", "--prompt", "--chroot", "--role",
              "--type", "--command-timeout", "--user", "--other-user")
_ENV_VALUE = ("-u", "-C", "-P", "--unset", "--chdir", "--argv0")
_SSH_VALUE = "BbcDEeFIiJLlmOopQRSWw"

_TEXT_RM = re.compile(r"(?<![\w.-])g?rm(?![\w.-])")
_TEXT_FIND = re.compile(r"(?<![\w.-])g?find(?![\w.-])")
_TEXT_DELETE = re.compile(r"(?<![\w-])-delete(?![\w-])")
_TEXT_REC = re.compile(r"(?<![\w-])-[A-Za-z]*[rR][A-Za-z]*(?![\w-])|(?<![\w-])--r[a-z]*(?![\w-])")
_TEXT_MARK = re.compile(r"[$`~]")
_TEXT_WORD = re.compile(r"""[^\s'"`;&|()<>=]+""")


def _text_protected(command):
    spelled = get_spellings(get_homes())["rm"][0]
    for m in _TEXT_WORD.finditer(command):
        t = m.group(0)
        if t.startswith("/"):
            if _key_levels(_lv(norm_plain(t))) in spelled:
                return t
    return None


def text_rule(command):
    """Fallback for unparsable commands: returns (rule, snippet) or None."""
    m = _TEXT_RM.search(command)
    if m and _TEXT_REC.search(command):
        if _TEXT_MARK.search(command) or _text_protected(command):
            return ("unparsable", command[m.start():m.start() + 200])
    m = _TEXT_FIND.search(command)
    if m and _TEXT_DELETE.search(command):
        if _TEXT_MARK.search(command) or _text_protected(command):
            return ("unparsable", command[m.start():m.start() + 200])
    return None


# ---------------------------------------------------------------------------
# command analysis
# ---------------------------------------------------------------------------
# A variable holds a set of possible values. Elements:
EMPTY = ("empty",)          # not set, or set to the empty string
UNK = ("unk",)              # not known: command output, environment, changed by read / eval ...
MK = ("mk",)                # a directory just created by mktemp
UNKSET = frozenset([UNK])
EMPTYSET = frozenset([EMPTY])
MKSET = frozenset([MK])
NO_VALUES = frozenset()
MKPATH = "/tmp/mktemp.XXXXXX"      # stands in for a mktemp directory when a path is judged
UNKCWD = frozenset([None])         # working directory possibilities: absolute paths, None = unknown
NOCHG = object()
MAX_ALTS = 64


class State(object):
    """Tracked shell state: the possible working directories and the possible values of
    the variables assigned in this command. A name that is absent has an unknown value."""
    __slots__ = ("cwd", "vars", "touched", "seen", "orig", "cwd_old", "cwd_seen", "reads", "tainted")

    def __init__(self, cwd, vars_=None, reads=None, tainted=False):
        self.cwd = cwd                # frozenset of absolute normalized paths and/or None
        self.vars = vars_ if vars_ is not None else {}
        self.touched = {}             # name -> value before its first change in the current window
        self.seen = {}                # name -> every value the name took in this state
        self.orig = {}                # name -> value it had when this state first changed it
        self.cwd_old = NOCHG          # working directory before its first change in the window
        self.cwd_seen = None          # every working directory this state has been in after a cd
        self.reads = reads if reads is not None else set()   # names read so far (shared)
        self.tainted = tainted        # source / eval / a function call may have set anything

    def fork(self):
        return State(self.cwd, dict(self.vars), self.reads, self.tainted)

    def fresh(self):
        return State(self.cwd, None, self.reads)

    def current(self, name):
        """The value set a name holds now. A name this command has not assigned reads as
        unknown when it was read before (it may hold an inherited value) and as empty
        otherwise; this is what an assignment that may not run is added to."""
        old = self.vars.get(name)
        if old is not None:
            return old
        if self.tainted or name in self.reads:
            return UNKSET
        return EMPTYSET

    def put(self, name, val):
        if name not in self.touched or name not in self.orig:
            cur = self.current(name)
            if name not in self.touched:
                self.touched[name] = cur
            if name not in self.orig:
                self.orig[name] = cur
        self.vars[name] = val
        self.seen[name] = self.seen.get(name, NO_VALUES) | val

    def drop(self, name):
        self.put(name, UNKSET)

    def drop_all(self):
        for name in list(self.vars):
            self.drop(name)
        self.tainted = True

    def set_cwd(self, cwd):
        if self.cwd_old is NOCHG:
            self.cwd_old = self.cwd
        self.cwd = cwd
        self.cwd_seen = (self.cwd_seen or NO_VALUES) | cwd

    def merge_child(self, child):
        """A branch / loop body / case arm ended: whatever it assigned may or may not have run."""
        for name, vals in child.seen.items():
            base = self.vars.get(name)
            self.put(name, (child.orig[name] if base is None else base) | vals)
        if child.cwd_seen is not None:
            self.set_cwd(self.cwd | child.cwd_seen)
        if child.tainted:
            self.tainted = True


class ListCtx(object):
    """One and-or list (commands joined by && / ||)."""
    __slots__ = ("pos", "all_and", "base", "seen", "cwd_base", "cwd_seen")

    def __init__(self):
        self.pos = 0
        self.all_and = True     # every connector so far in this and-or list was &&
        self.base = {}          # name -> its value set before the first conditional change
        self.seen = {}          # name -> values assigned at conditional positions
        self.cwd_base = None    # working directories when the list started (once a cd ran)
        self.cwd_seen = None    # working directories after the cds of the list


def is_assign(w):
    m = _NAME_ASSIGN.match(w.text)
    return bool(m) and not any(w.q[:m.end()])


def skip_opts(args, short_val="", long_val=()):
    """Skip leading option words. Returns (index of first non-option word, option names)."""
    i = 0
    n = len(args)
    flags = []
    while i < n:
        w = args[i]
        t = w.text
        if w.expands:
            break
        if t == "--":
            i += 1
            break
        if len(t) < 2 or t[0] != "-":
            break
        if t.startswith("--"):
            name = t.split("=", 1)[0]
            flags.append(name)
            if "=" not in t and name in long_val:
                i += 2
            else:
                i += 1
            continue
        body = t[1:]
        step = 1
        for k, ch in enumerate(body):
            flags.append(ch)
            if ch in short_val:
                if k == len(body) - 1:
                    step = 2
                break
        i += step
    return min(i, n), flags


def has_unquoted_expansion(raw):
    """True when raw contains a $ expansion or backquote outside quotes."""
    n = len(raw)
    i = 0
    try:
        while i < n:
            c = raw[i]
            if c == "\\":
                i += 2
            elif c == "'":
                i = _skip_squote(raw, i)
            elif c == '"':
                i = _skip_dq(raw, i)
            elif c == "`":
                return True
            elif c == "$":
                nxt = raw[i + 1] if i + 1 < n else ""
                if nxt == "'":
                    i = _skip_ansi(raw, i + 1)
                elif nxt == '"':
                    i += 1
                elif nxt and (nxt in "({_@*#?!$-" or nxt.isalnum()):
                    return True
                else:
                    i += 1
            else:
                i += 1
    except Unparsable:
        return False
    return False


def recursive_option(t):
    if t.startswith("--"):
        name = t.split("=", 1)[0]
        return len(name) >= 3 and "--recursive".startswith(name)
    return len(t) > 1 and t[0] == "-" and ("r" in t[1:] or "R" in t[1:])


_VAR_REF = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
_READ_REF = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")
_DOT = Word(".", ".", [0], False, [])


class Analyzer(object):
    def __init__(self, cwd):
        homes = get_homes()
        self.homes = homes
        self.spell = get_spellings(homes)
        start = None
        if isinstance(cwd, str) and cwd.startswith("/"):
            start = norm_plain(cwd)
        self.start_cwd = start
        self.trap_stack = []
        self.funcs = set()
        self.func_bodies = {}
        self.in_call = set()
        self.call_budget = 200
        self.judged = set()
        # names that normally arrive from the environment count as read before any assignment
        self.reads = set(ENV_NAMES)
        self.reads.update(k for k in os.environ if _ENV_NAME.match(k))

    def new_state(self, cwd, vars_=None):
        return State(cwd, vars_, self.reads)

    # -- entry -------------------------------------------------------------
    def run(self, command):
        st = self.new_state(frozenset([self.start_cwd]))
        self.run_script(command, 0, st, False)

    def run_script(self, text, depth, st, remote):
        if depth > MAX_DEPTH:
            raise Unparsable("nesting too deep")
        items = lex(text)
        self.trap_stack.append([])
        try:
            self.run_items(items, st, depth, remote)
        except BaseException:
            self.trap_stack.pop()
            raise
        for script, d, r in self.trap_stack.pop():
            self.run_script(script, d, st.fork(), r)

    # -- control flow ----------------------------------------------------------
    @staticmethod
    def merge_list(lc, st):
        """The and-or list ended (or a || was reached): every assignment and cd made at a
        position that may not have run adds its value to what the name / cwd held before."""
        for name, base in lc.base.items():
            st.put(name, base | lc.seen[name])
        if lc.cwd_seen is not None:
            st.set_cwd(lc.cwd_base | lc.cwd_seen)

    def run_items(self, items, st, depth, remote):
        frames = []
        lc = ListCtx()
        seg = []

        def end_list():
            nonlocal lc
            self.merge_list(lc, st)
            lc = ListCtx()

        def push_frame(kind):
            nonlocal st
            end_list()
            frames.append((kind, st))
            st = st.fork()

        def pop_frame(kind):
            nonlocal st
            end_list()
            if frames and frames[-1][0] == kind:
                child = st
                st = frames.pop()[1]
                st.merge_child(child)

        for item in items:
            if isinstance(item, Mark):
                if item.kind == "case_open":
                    push_frame("case")
                else:
                    pop_frame("case")
                continue
            cmd = item
            skip = False
            if not seg and cmd.words:
                words = cmd.words
                idx = 0
                while idx < len(words) and words[idx].plain() and words[idx].text in KEYWORDS:
                    kw = words[idx].text
                    idx += 1
                    if kw in ("then", "do"):
                        push_frame("body")
                    elif kw == "else":
                        pop_frame("body")
                        push_frame("body")
                    elif kw == "elif":
                        pop_frame("body")
                    elif kw in ("fi", "done"):
                        pop_frame("body")
                    elif kw == "esac":
                        pop_frame("case")
                    elif kw in ("for", "select"):
                        if idx < len(words) and words[idx].plain():
                            st.drop(words[idx].text)
                        skip = True
                        break
                    elif kw == "case":
                        skip = True
                        break
                if idx:
                    c2 = Cmd()
                    c2.words = words[idx:]
                    c2.extra = cmd.extra
                    c2.heredocs = cmd.heredocs
                    c2.herestrings = cmd.herestrings
                    c2.sep = cmd.sep
                    c2.group = cmd.group
                    cmd = c2
            if skip:
                self.run_subs(cmd, depth, st, remote)
                if cmd.sep in ("&&", "||"):
                    lc.pos += 1
                    if cmd.sep == "||":
                        lc.all_and = False
                else:
                    end_list()
                continue
            if not (cmd.words or cmd.group is not None or cmd.extra or cmd.heredocs):
                if not seg:
                    if cmd.sep not in ("&&", "||"):
                        end_list()
                continue
            seg.append(cmd)
            if cmd.sep in ("|",):
                continue
            ends = self.run_element(seg, cmd.sep, lc, st, depth, remote)
            seg = []
            if ends:
                end_list()
        if seg:
            self.run_element(seg, None, lc, st, depth, remote)
        end_list()
        while frames:
            child = st
            st = frames.pop()[1]
            st.merge_child(child)

    def run_element(self, seg, sep, lc, st, depth, remote):
        """Run one pipeline (or one background command). Returns True when the and-or
        list ends after it."""
        pos = lc.pos
        cond_ok = pos == 0 or lc.all_and
        if len(seg) == 1 and sep != "&":
            saved_t, saved_c = st.touched, st.cwd_old
            st.touched = {}
            st.cwd_old = NOCHG
            try:
                self.run_cmd(seg[0], depth, st, remote, None)
            finally:
                touched, c_old = st.touched, st.cwd_old
                merged = dict(touched)
                merged.update(saved_t)
                st.touched = merged
                st.cwd_old = saved_c if saved_c is not NOCHG else c_old
            if pos > 0:
                for name, old in touched.items():
                    cur = st.vars[name]
                    if name not in lc.base:
                        lc.base[name] = old
                    lc.seen[name] = lc.seen.get(name, NO_VALUES) | cur
                    if not cond_ok:
                        st.put(name, old | cur)
            if c_old is not NOCHG and st.cwd != c_old:
                if lc.cwd_base is None:
                    lc.cwd_base = c_old
                lc.cwd_seen = (lc.cwd_seen or NO_VALUES) | st.cwd
                if not (sep == "&&" and cond_ok):
                    st.set_cwd(c_old | st.cwd)
        else:
            texts = []
            last = None
            for k, cmd in enumerate(seg):
                child = st.fork()
                self.run_cmd(cmd, depth, child, remote, list(texts))
                texts.extend(self.stdin_texts(cmd, st))
                if k == len(seg) - 1 and sep != "&":
                    last = child
            if last is not None:
                # the last segment may run in the current shell (zsh, lastpipe)
                for name, vals in last.seen.items():
                    base = st.vars.get(name)
                    st.put(name, (last.orig[name] if base is None else base) | vals)
                if last.cwd_seen is not None:
                    st.set_cwd(st.cwd | last.cwd_seen)
        lc.pos += 1
        if sep == "||":
            self.merge_list(lc, st)
            lc.all_and = False
            return False
        if sep == "&&":
            return False
        return True

    def stdin_texts(self, cmd, st):
        """Text a pipeline segment writes to the next one: heredoc / here-string bodies and the
        literal arguments of echo / printf."""
        out = []
        for hd in cmd.heredocs:
            out.append(hd.body)
        for hs in cmd.herestrings:
            out.extend(self.text_alts(hs, st))
        words = cmd.words
        idx = 0
        while idx < len(words) and is_assign(words[idx]):
            idx += 1
        if idx < len(words) and not words[idx].expands:
            base = words[idx].text
            args = words[idx + 1:]
            if base == "echo":
                i = 0
                while i < len(args) and args[i].plain() and re.match(r"-[neE]+\Z", args[i].text):
                    i += 1
                out.extend(self.join_alts(args[i:], st))
            elif base == "printf" and args:
                for combo in self.alt_product([self.text_alts(a, st) for a in args]):
                    out.append(self.render_printf(combo[0], list(combo[1:])))
        return out

    @staticmethod
    def render_printf(fmt, vals):
        it = iter(vals)
        used = [False]

        def rep(m):
            try:
                v = next(it)
                used[0] = True
                return v
            except StopIteration:
                return ""
        res = re.sub(r"%[-0-9.]*[sbdq]", rep, fmt)
        res = res.replace("\\n", "\n").replace("\\t", "\t")
        if vals and not used[0]:
            res += "\n" + "\n".join(vals)
        return res

    # -- one simple command ------------------------------------------------
    def run_subs(self, cmd, depth, st, remote):
        for w in cmd.words:
            for sub in w.subs:
                self.run_script(sub, depth + 1, st.fork(), remote)
        for w in cmd.extra:
            for sub in w.subs:
                self.run_script(sub, depth + 1, st.fork(), remote)

    def run_cmd(self, cmd, depth, st, remote, piped):
        words = cmd.words
        idx = 0
        assigns = []
        n = len(words)
        while idx < n and is_assign(words[idx]):
            assigns.append(words[idx])
            idx += 1
        rest = words[idx:]
        self.note_reads(cmd)
        if not rest:
            for w in assigns:
                self.apply_assign(w, st)
        else:
            self.exec_command(rest, cmd, st, depth, remote, piped)
        if cmd.group is not None:
            head = rest[0].text if rest and rest[0].plain() else ""
            if head == "function":
                body_state = self.new_state(UNKCWD, dict(st.vars))
                body_state.tainted = st.tainted
                if len(rest) > 1 and rest[1].plain():
                    self.func_bodies[rest[1].text] = cmd.group.items
                self.run_items(cmd.group.items, body_state, depth, remote)
            elif head == "coproc" or cmd.group.kind == "sub":
                self.run_items(cmd.group.items, st.fork(), depth, remote)
            else:
                self.run_items(cmd.group.items, st, depth, remote)
        self.run_subs(cmd, depth, st, remote)
        for hd in cmd.heredocs:
            if not hd.quoted and id(hd) not in self.judged:
                for sub in heredoc_substitutions(hd.body):
                    self.run_script(sub, depth + 1, st.fork(), remote)

    def note_reads(self, cmd):
        """Remember the variable names this command reads (before its own assignments run)."""
        for w in cmd.words:
            if w.expands:
                for m in _READ_REF.finditer(w.text):
                    self.reads.add(m.group(1))
        for w in cmd.extra:
            if w.expands:
                for m in _READ_REF.finditer(w.text):
                    self.reads.add(m.group(1))

    def apply_assign(self, w, st):
        m = _NAME_ASSIGN.match(w.text)
        name = m.group(0).rstrip("+=")
        if m.group(0).endswith("+="):
            st.drop(name)
            return
        if self.is_mktemp_value(w):
            st.put(name, MKSET)
            return
        lit = self.literal_value(w, m.end())
        st.put(name, UNKSET if lit is None else lit)

    @staticmethod
    def literal_value(w, start):
        """The value set of a NAME=<value> word: {empty}, {literal path}, or None when the value
        is not a plain literal."""
        if w.expands or w.subs:
            return None
        v = w.text[start:]
        if v == "":
            return EMPTYSET
        if v.startswith("~"):
            return None
        if any(ch in v for ch in "$`*?[\n"):
            return None
        return frozenset([("lit", v)])

    def is_mktemp_value(self, w):
        raw = w.raw
        eq = raw.find("=")
        if eq < 0 or len(w.subs) != 1:
            return False
        v = raw[eq + 1:]
        if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
            v = v[1:-1]
        if not ((v.startswith("$(") and v.endswith(")")) or (v.startswith("`") and v.endswith("`"))):
            return False
        try:
            cmds = lex(w.subs[0])
        except Unparsable:
            return False
        if len(cmds) != 1 or isinstance(cmds[0], Mark) or not cmds[0].words or cmds[0].heredocs:
            return False
        head = cmds[0].words[0]
        return (not head.expands) and head.text.rsplit("/", 1)[-1] == "mktemp"

    @staticmethod
    def mk_rest_safe(rest):
        """What follows a mktemp directory in a path: only plain names (no expansion, glob or ..)."""
        return not (any(ch in rest for ch in "$`*?[{\n") or ".." in rest.split("/"))

    def text_alts(self, w, st):
        """Texts of a word as a nested shell sees it. Variables of the outer shell with known
        values are substituted (except inside single quotes); a name with several possible
        values gives one text per value. Unknown values stay as written."""
        t = w.text
        if not w.expands or "$" not in t:
            return [t]
        pieces = []
        last = 0
        for m in _VAR_REF.finditer(t):
            if w.q[m.start()] == QS:
                continue
            vals = st.vars.get(m.group(1) or m.group(2))
            if vals is None:
                continue
            opts = []
            for p in sorted(vals):
                if p[0] == "lit":
                    opts.append(p[1])
                elif p == EMPTY:
                    opts.append("")
                elif p == MK and self.mk_rest_safe(t[m.end():]):
                    opts.append(MKPATH)
                else:
                    opts.append(m.group(0))
            pieces.append((t[last:m.start()], opts))
            last = m.end()
        if not pieces:
            return [t]
        tail = t[last:]
        outs = [""]
        for lead, opts in pieces:
            outs = [o + lead + x for o in outs for x in opts]
            if len(outs) > MAX_ALTS:
                return [t]
        outs = [o + tail for o in outs]
        res = []
        for o in outs:
            if o not in res:
                res.append(o)
        return res

    @staticmethod
    def alt_product(lists):
        """All combinations (tuples) of one text per list; one combination of the first texts
        when there would be too many."""
        combos = [()]
        for opts in lists:
            combos = [c + (x,) for c in combos for x in opts]
            if len(combos) > MAX_ALTS:
                return [tuple(o[0] for o in lists)]
        return combos

    def join_alts(self, words, st):
        """The words joined by spaces, one text per combination of possible values."""
        if not words:
            return [""]
        return [" ".join(c) for c in self.alt_product([self.text_alts(w, st) for w in words])]

    # -- command dispatch ----------------------------------------------------
    def exec_command(self, words, cmd, st, depth, remote, piped=None):
        """Handle one command whose words start at the command name. Returns True when
        the command (after unwrapping) was an rm."""
        guard = 0
        while words and guard < 32:
            guard += 1
            w = words[0]
            if w.expands:
                return self.expansion_head(words, cmd, st, depth, remote, piped)
            base = w.text.rsplit("/", 1)[-1] if w.text.startswith("/") else w.text
            args = words[1:]
            if base in ("rm", "grm"):
                self.do_rm(args, st, remote)
                return True
            if base in ("find", "gfind"):
                return self.do_find(args, cmd, st, depth, remote)
            peeled = self.peel(base, args, st)
            if peeled is not None:
                new_words, scripts = peeled
                for script in scripts:
                    self.run_script(script, depth + 1, st.fresh(), remote)
                if new_words is None:
                    return False
                words = new_words
                continue
            if base in SHELLS:
                self.do_shell(args, cmd, st, depth, remote, piped)
            elif base == "eval":
                for script in self.join_alts(args, st):
                    self.run_script(script, depth + 1, st, remote)
                for a in args:
                    for text in self.substitution_scripts(a, st):
                        self.run_script(text, depth + 1, st, remote)
                st.drop_all()
            elif base in ("source", "."):
                st.drop_all()
            elif base == "trap":
                self.do_trap(args, st, depth, remote)
            elif base in ("cd", "pushd"):
                self.do_cd(args, st)
            elif base == "popd":
                st.set_cwd(UNKCWD)
            elif base == "ssh":
                self.do_ssh(args, cmd, st, depth, piped)
            elif base == "su":
                self.do_su(args, st, depth, remote)
            elif base == "function":
                if args and args[0].plain():
                    self.funcs.add(args[0].text)
            elif base in ASSIGN_BUILTINS:
                self.do_assign_builtin(base, args, st)
            elif base in CLEAR_BUILTINS:
                for a in args:
                    if a.plain() and not a.text.startswith("-"):
                        st.drop(a.text.split("[", 1)[0])
            elif base == "read":
                self.do_read(args, st)
            elif base in ("mapfile", "readarray"):
                self.do_mapfile(args, st)
            elif base == "getopts":
                i, _ = skip_opts(args)
                if i + 1 < len(args) and args[i + 1].plain():
                    st.drop(args[i + 1].text)
            elif base == "printf":
                for k, a in enumerate(args):
                    if a.plain() and a.text == "-v" and k + 1 < len(args):
                        st.drop(args[k + 1].text.split("[", 1)[0])
                        break
            elif base in self.funcs:
                self.call_function(base, st, depth, remote)
                st.drop_all()
            return False
        return False

    def call_function(self, name, st, depth, remote):
        """Judge the body of a function defined in this command again with the values the
        variables hold at the call."""
        body = self.func_bodies.get(name)
        if body is None or name in self.in_call or self.call_budget <= 0:
            return
        self.call_budget -= 1
        self.in_call.add(name)
        try:
            state = self.new_state(UNKCWD, dict(st.vars))
            state.tainted = st.tainted
            self.run_items(body, state, depth, remote)
        finally:
            self.in_call.discard(name)

    def expansion_head(self, words, cmd, st, depth, remote, piped):
        """The command name is an expansion: judge the rest of the words as a command, and
        treat a recursive option anywhere as an rm."""
        w = words[0]
        if w.text in ("$SHELL", "${SHELL}"):
            self.do_shell(words[1:], cmd, st, depth, remote, piped)
            return False
        k = 1
        while k < len(words) and words[k].expands:
            k += 1
        rest = words[k:]
        was_rm = False
        if rest:
            was_rm = self.exec_command(rest, cmd, st, depth, remote, piped)
        if not was_rm:
            for a in words[1:]:
                if a.plain() and a.text == "--":
                    break
                if a.plain() and recursive_option(a.text):
                    self.do_rm(words[1:], st, remote)
                    break
        return was_rm

    def do_assign_builtin(self, base, args, st):
        flags = ""
        for a in args:
            if a.plain() and a.text.startswith("-") and len(a.text) > 1:
                flags += a.text[1:]
        nameref = "n" in flags
        for a in args:
            if a.plain() and a.text.startswith("-"):
                continue
            if is_assign(a):
                if nameref:
                    st.drop(_NAME_ASSIGN.match(a.text).group(0).rstrip("+="))
                else:
                    self.apply_assign(a, st)
            elif a.plain():
                if nameref or base in ("local", "declare", "typeset"):
                    st.drop(a.text.split("[", 1)[0])

    def do_read(self, args, st):
        i = 0
        n = len(args)
        names = []
        while i < n:
            t = args[i].text
            if args[i].plain() and t.startswith("-") and len(t) > 1:
                letters = t[1:]
                if letters[-1] in "pudnNta" and len(letters) >= 1 and letters[-1] in "pudnNt":
                    i += 2
                    continue
                if letters[-1] == "a":
                    if i + 1 < n:
                        names.append(args[i + 1].text)
                    i += 2
                    continue
                i += 1
                continue
            names.append(t)
            i += 1
        if not names:
            names = ["REPLY"]
        for nm in names:
            st.drop(nm.split("[", 1)[0])

    def do_mapfile(self, args, st):
        i = 0
        n = len(args)
        names = []
        while i < n:
            t = args[i].text
            if args[i].plain() and t.startswith("-") and len(t) > 1:
                i += 2 if t[-1] in "dnOsuCc" else 1
                continue
            names.append(t)
            i += 1
        st.drop((names[0] if names else "MAPFILE").split("[", 1)[0])

    # -- wrappers --------------------------------------------------------------
    def peel(self, base, args, st):
        """For wrapper commands returns (remaining words or None, nested scripts); None when
        base is not a wrapper."""
        if base == "command":
            i, fl = skip_opts(args)
            if "v" in fl or "V" in fl:
                return (None, [])
            return (args[i:], [])
        if base in ("builtin", "nohup", "setsid", "unbuffer", "noglob", "nocorrect", "chronic",
                    "busybox", "coproc"):
            i, _ = skip_opts(args)
            return (args[i:], [])
        if base == "exec":
            i, _ = skip_opts(args, "a")
            return (args[i:], [])
        if base == "time":
            i, _ = skip_opts(args, "fo")
            return (args[i:], [])
        if base == "nice":
            i, _ = skip_opts(args, "n", ("--adjustment",))
            return (args[i:], [])
        if base == "ionice":
            i, _ = skip_opts(args, "cnpPu")
            return (args[i:], [])
        if base == "stdbuf":
            i, _ = skip_opts(args, "ioe")
            return (args[i:], [])
        if base == "caffeinate":
            i, _ = skip_opts(args, "tw")
            return (args[i:], [])
        if base == "flock":
            i, _ = skip_opts(args, "wE", ("--timeout", "--conflict-exit-code"))
            return (args[i + 1:], [])
        if base == "watch":
            i, _ = skip_opts(args, "n", ("--interval",))
            rest = args[i:]
            if rest:
                return (None, self.join_alts(rest, st))
            return (None, [])
        if base in ("sudo", "doas"):
            i, fl = skip_opts(args, "CDghpRrTtUu" if base == "sudo" else "uC",
                              _SUDO_LONG if base == "sudo" else ())
            while i < len(args) and is_assign(args[i]):
                i += 1
            if base == "sudo" and ("s" in fl or "i" in fl or "--login" in fl or "--shell" in fl):
                rest = args[i:]
                if rest:
                    return (None, self.join_alts(rest, st))
                return (None, [])
            return (args[i:], [])
        if base == "env":
            return self.peel_env(args, st)
        if base in ("timeout", "gtimeout"):
            i, _ = skip_opts(args, "ks", ("--kill-after", "--signal"))
            return (args[i + 1:], [])
        if base == "xargs":
            i, _ = skip_opts(args, "adEIJLnPRSs", _XARGS_LONG)
            return (args[i:], [])
        if base == "parallel":
            return self.peel_parallel(args, st)
        return None

    def peel_env(self, args, st):
        i = 0
        n = len(args)
        script = None
        while i < n:
            a = args[i]
            t = a.text
            if a.expands:
                break
            if t == "--":
                i += 1
                break
            if t in ("-S", "--split-string"):
                script = self.text_alts(args[i + 1], st) if i + 1 < n else [""]
                i += 2
            elif t.startswith("-S") and len(t) > 2 and not t.startswith("--"):
                script = [t[2:]]
                i += 1
            elif t.startswith("--split-string="):
                script = [t.split("=", 1)[1]]
                i += 1
            elif len(t) > 1 and t[0] == "-":
                i += 2 if t in _ENV_VALUE else 1
            else:
                break
        while i < n and (is_assign(args[i]) or args[i].text == "-"):
            i += 1
        if script is not None:
            return (None, [(sc + " " + tail).strip() for sc in script for tail in self.join_alts(args[i:], st)])
        return (args[i:], [])

    def peel_parallel(self, args, st):
        i, _ = skip_opts(args, "jnNaSLlsdI", _PARALLEL_LONG)
        rest = args[i:]
        colon = None
        for k, w in enumerate(rest):
            if w.plain() and w.text in (":::", "::::", ":::+", "::::+"):
                colon = k
                break
        if colon is None:
            return (rest, [])
        cmdw = rest[:colon]
        argsw = [a for a in rest[colon + 1:] if not (a.plain() and a.text in (":::", "::::", ":::+", "::::+"))]
        if not cmdw:
            return (None, [])
        if len(cmdw) == 1 and re.search(r"\s", cmdw[0].text):
            base_scripts = self.text_alts(cmdw[0], st)
        else:
            base_scripts = [" ".join(a.raw for a in cmdw)]
        out = []
        for base_script in base_scripts:
            if "{}" not in base_script:
                base_script += " {}"
            if not argsw:
                out.append(base_script)
            else:
                out.extend(base_script.replace("{}", a.raw) for a in argsw[:MAX_PARALLEL_ARGS])
        return (None, out)

    # -- rm ------------------------------------------------------------------
    def do_rm(self, args, st, remote):
        rec = False
        done = False
        targets = []
        for w in args:
            t = w.text
            if not done and t == "--" and w.plain():
                done = True
                continue
            if not done and len(t) > 1 and t[0] == "-":
                if recursive_option(t):
                    rec = True
                continue
            targets.append(w)
        if not rec:
            # options may arrive through an unquoted expansion standing before the first
            # target (rm $OPTS "$X"): that word is taken as the option word
            done = False
            for w in args:
                t = w.text
                if not done and t == "--" and w.plain():
                    break
                if not done and len(t) > 1 and t[0] == "-" and not w.expands:
                    continue
                if has_unquoted_expansion(w.raw):
                    rec = True
                    targets = [x for x in targets if x is not w]
                break
        if not rec:
            return
        for w in targets:
            self.judge_target(w, st, remote)

    def expand_word(self, w, st):
        """The word with every tracked variable replaced by each of its possible values.
        Returns a list of (text, q) alternatives, or None when some value is not known (an
        untracked name, an unknown value, or an expansion form that cannot be resolved)."""
        if not w.expands:
            return [(w.text, w.q)]
        t = w.text
        if w.subs or (t.startswith("~") and not w.q[0]):
            return None
        refs = []
        starts = set()
        for m in _VAR_REF.finditer(t):
            if w.q[m.start()] == QS:
                continue
            refs.append(m)
            starts.add(m.start())
        for k, ch in enumerate(t):
            if ch == "$" and w.q[k] != QS and k not in starts:
                return None
        if not refs:
            return [(t, w.q)]
        options = []
        for m in refs:
            vals = st.vars.get(m.group(1) or m.group(2))
            if not vals or UNK in vals:
                return None
            rest = t[m.end():]
            if "\n" in rest or ".." in rest.split("/"):
                return None
            if (rest and rest[0] != "/") or (m.start() > 0 and t[m.start() - 1] != "/"):
                return None      # the name must be a whole path component ("${D}y" is another word)
            quoted = w.refs.get(m.start(), False)
            opts = []
            for p in sorted(vals):
                if p == EMPTY:
                    opts.append("")
                elif p == MK:
                    if m.start() != 0 or not self.mk_rest_safe(rest):
                        return None
                    opts.append(MKPATH)
                else:
                    if not quoted and any(ch.isspace() for ch in p[1]):
                        return None      # an unquoted use would be split into several words
                    opts.append(p[1])
            options.append(opts)
        combos = [()]
        for opts in options:
            combos = [c + (x,) for c in combos for x in opts]
            if len(combos) > 256:
                return None
        out = []
        for combo in combos:
            chars = []
            qs = []
            last = 0
            for m, val in zip(refs, combo):
                chars.append(t[last:m.start()])
                qs.extend(w.q[last:m.start()])
                chars.append(val)
                qs.extend([QD] * len(val))
                last = m.end()
            chars.append(t[last:])
            qs.extend(w.q[last:])
            out.append(("".join(chars), qs))
        return out

    def judge_target(self, w, st, remote):
        if w.text == "" and not w.expands:
            return
        if not w.expands and w.text.startswith("~"):
            raise Hit("tilde", w.raw)
        alts = self.expand_word(w, st)
        if alts is None:
            raise Hit("expansion", w.raw)
        for text, q in alts:
            if text == "":
                continue            # an empty argument: rm reports an error and removes nothing
            for t, tq in brace_expand(text, q):
                rule = self.check_target(t, tq, st, remote, False)
                if rule:
                    raise Hit(rule, w.raw)

    def check_target(self, text, q, st, remote, find):
        """Rule name for a target path (already free of expansions and a leading ~). A relative
        path is judged once for every possible working directory."""
        if text == "":
            return None
        if text.startswith("/"):
            return self.check_one(text, q, None, remote, find, True)
        for cwd in sorted(st.cwd, key=lambda c: (c is not None, c or "")):
            rule = self.check_one(text, q, cwd, remote, find, False)
            if rule:
                return rule
        return None

    def check_one(self, text, q, cwd, remote, find, absolute):
        key = "find" if find else "rm"
        if remote:
            key += "_remote"
        spelled, by_depth = self.spell[key]
        levels = split_levels(text, q)
        trailing = text.endswith("/") or text == "." or text.endswith("/.")
        if absolute:
            levels = normalize_levels(levels)
        elif cwd is not None:
            levels = normalize_levels([Level(c) for c in _lv(cwd)] + levels)
        else:
            parts = []
            for lv in levels:
                if not lv.glob:
                    if lv.lit == "" or lv.lit == ".":
                        continue
                    if lv.lit == "..":
                        if parts and parts[-1] != "..":
                            parts.pop()
                        else:
                            parts.append("..")
                        continue
                parts.append(lv)
            if not parts or parts[0] == ".." or parts[0].glob:
                return "unknown-cwd"
            return None
        if any(lv.glob for lv in levels):
            return "protected-glob" if glob_protected(levels, by_depth) else None
        if literal_hit([lv.lit for lv in levels], trailing, spelled):
            return "protected-path"
        return None

    # -- find ----------------------------------------------------------------
    def do_find(self, args, cmd, st, depth, remote):
        i = 0
        n = len(args)
        starts = []
        while i < n:
            t = args[i].text
            if not args[i].plain():
                break
            if t in ("-H", "-L", "-P", "-E", "-X", "-x", "-s", "--") or re.match(r"-O\d?\Z", t):
                i += 1
            elif t == "-D":
                i += 2
            else:
                break
        while i < n:
            w = args[i]
            t = w.text
            if w.plain() and ((len(t) > 1 and t[0] == "-") or t in ("(", ")", "!", ",")):
                break
            starts.append(w)
            i += 1
        expr = args[i:]
        has_delete = False
        execs = []
        k = 0
        while k < len(expr):
            w = expr[k]
            if w.plain() and w.text == "-delete":
                has_delete = True
            elif w.plain() and w.text in ("-exec", "-execdir", "-ok", "-okdir"):
                j = k + 1
                cmd_words = []
                while j < len(expr) and expr[j].text not in (";", "+"):
                    cmd_words.append(expr[j])
                    j += 1
                execs.append(cmd_words)
                k = j
            k += 1
        exec_rm = any(self.peek_is_rm(c) for c in execs)
        if has_delete or exec_rm:
            for w in (starts or [_DOT]):
                self.judge_find_start(w, st, remote)
        empty = Cmd()
        for c in execs:
            self.exec_command(c, empty, st, depth, remote)
        return False

    def peek_is_rm(self, words):
        guard = 0
        while words and guard < 32:
            guard += 1
            w = words[0]
            if w.expands:
                return False
            base = w.text.rsplit("/", 1)[-1] if w.text.startswith("/") else w.text
            if base in ("rm", "grm"):
                return True
            peeled = self.peel(base, words[1:], self.new_state(UNKCWD))
            if peeled is None or peeled[0] is None:
                return False
            words = peeled[0]
        return False

    def judge_find_start(self, w, st, remote):
        if w.text == "" and not w.expands:
            return
        if not w.expands and w.text.startswith("~"):
            raise Hit("tilde", w.raw)
        alts = self.expand_word(w, st)
        if alts is None:
            raise Hit("expansion", w.raw)
        for text, q in alts:
            if text == "":
                continue
            rule = self.check_target(text, q, st, remote, True)
            if rule:
                raise Hit(rule, w.raw)

    # -- nested shells -------------------------------------------------------
    @staticmethod
    def shell_args(args):
        """Returns (word holding the -c string or None, True when the shell reads a program
        from standard input)."""
        i = 0
        n = len(args)
        c_seen = False
        s_flag = False
        while i < n:
            t = args[i].text
            if t == "--":
                i += 1
                break
            if len(t) > 1 and t[0] in "-+":
                if t.startswith("--"):
                    i += 2 if t in ("--rcfile", "--init-file") else 1
                    continue
                letters = t[1:]
                if t[0] == "-" and "c" in letters:
                    c_seen = True
                if t[0] == "-" and "s" in letters:
                    s_flag = True
                i += 2 if ("o" in letters or "O" in letters) else 1
                continue
            break
        if c_seen:
            return (args[i] if i < n else None), False
        return None, (s_flag or i >= n)

    def do_shell(self, args, cmd, st, depth, remote, piped=None):
        cw, reads_stdin = self.shell_args(args)
        if cw is not None:
            for script in self.text_alts(cw, st):
                self.run_script(script, depth + 1, st.fresh(), remote)
            for text in self.substitution_scripts(cw, st):
                self.run_script(text, depth + 1, st.fresh(), remote)
        if reads_stdin:
            self.feed_stdin(cmd, st, depth, remote, piped, st.fresh)

    def substitution_scripts(self, w, st):
        """Texts printed by a command substitution whose body is cat / echo / printf of literal
        text (bash -c "$(cat <<'EOF' ... EOF)"): the shell runs them as a program."""
        out = []
        for sub in w.subs:
            try:
                items = lex(sub)
            except Unparsable:
                continue
            for it in items:
                if isinstance(it, Mark) or not it.words or it.words[0].expands:
                    continue
                if it.words[0].text in ("cat", "echo", "printf"):
                    out.extend(self.stdin_texts(it, st))
        return out

    def feed_stdin(self, cmd, st, depth, remote, piped, make_state):
        for hd in cmd.heredocs:
            self.judged.add(id(hd))
            self.run_script(hd.body, depth + 1, make_state(), remote)
        for hs in cmd.herestrings:
            for script in self.text_alts(hs, st):
                self.run_script(script, depth + 1, make_state(), remote)
        for text in (piped or ()):
            self.run_script(text, depth + 1, make_state(), remote)

    def do_su(self, args, st, depth, remote):
        for k, w in enumerate(args):
            if w.text in ("-c", "--command") and k + 1 < len(args):
                for script in self.text_alts(args[k + 1], st):
                    self.run_script(script, depth + 1, st.fresh(), remote)
                return

    def do_trap(self, args, st, depth, remote):
        i, _ = skip_opts(args)
        if i < len(args):
            for script in self.text_alts(args[i], st):
                if script and script != "-":
                    self.trap_stack[-1].append((script, depth + 1, remote))

    def do_ssh(self, args, cmd, st, depth, piped):
        i, _ = skip_opts(args, _SSH_VALUE)
        rest = args[i + 1:] if i < len(args) else []
        j = 0
        cmd_words = []
        while j < len(rest):
            t = rest[j].text
            if t == "--":
                cmd_words = rest[j + 1:]
                break
            if len(t) > 1 and t[0] == "-" and not rest[j].expands:
                j += 2 if (t[-1] in _SSH_VALUE and not t.startswith("--")) else 1
                continue
            cmd_words = rest[j:]
            break
        if cmd_words:
            for script in self.join_alts(cmd_words, st):
                self.run_script(script, depth + 1, self.new_state(UNKCWD), True)
        stdin_to_shell = not cmd_words
        if cmd_words and not cmd_words[0].expands and cmd_words[0].text in SHELLS:
            stdin_to_shell = self.shell_args(cmd_words[1:])[1]
        if stdin_to_shell:
            self.feed_stdin(cmd, st, depth, True, piped, lambda: self.new_state(UNKCWD))

    def do_cd(self, args, st):
        """cd as if it succeeded: the working directory becomes every value the argument can take.
        Whether it may have failed is handled by the caller (union with the old directory)."""
        i, _ = skip_opts(args, "")
        rest = args[i:]
        home0 = self.homes[0] if self.homes else None
        if not rest:
            st.set_cwd(frozenset([home0]))
            return
        a = rest[0]
        t = a.text
        has_glob = any((not a.q[k]) and ch in "*?[" for k, ch in enumerate(t))
        if a.subs or t == "-" or has_glob:
            st.set_cwd(UNKCWD)
            return
        if not a.expands:
            if t == "~" or t.startswith("~/"):
                st.set_cwd(frozenset([norm_plain(home0 + "/" + t[2:]) if home0 else None]))
                return
            if t.startswith("~") or (t.startswith("+") and t[1:].isdigit()):
                st.set_cwd(UNKCWD)
                return
        alts = self.expand_word(a, st)
        if alts is None:
            st.set_cwd(UNKCWD)
            return
        out = set()
        for text, _q in alts:
            if text == "":
                if t == "" or all(a.refs.get(k, False) for k in a.refs):
                    out.update(st.cwd)       # cd "" stays where it is
                else:
                    out.add(home0)           # an unquoted empty expansion leaves a bare cd
            elif text.startswith("/"):
                out.add(norm_plain(text))
            else:
                for c in st.cwd:
                    out.add(None if c is None else norm_plain(c + "/" + text))
        st.set_cwd(frozenset(out))


# ---------------------------------------------------------------------------
# public judgement
# ---------------------------------------------------------------------------
def judge(command, cwd=None):
    """Returns None to allow, or (rule, target text) to reject. Pure: no I/O."""
    try:
        Analyzer(cwd).run(command)
        return None
    except Hit as h:
        return (h.rule, h.target)
    except Exception:
        # unparsable input or an internal error: use the text rule; if that fails too, reject
        try:
            return text_rule(command)
        except Exception:
            return ("unparsable", command[:200])


# ---------------------------------------------------------------------------
# hook entry
# ---------------------------------------------------------------------------
RULE_TEXT = {
    "expansion": "目标含变量展开、命令替换或反引号(没被单引号包住的 $ 或反引号)",
    "tilde": "目标以 ~ 开头",
    "protected-path": "目标是家目录、家目录的上层目录,或系统目录",
    "protected-glob": "目标里的通配符落在家目录、家目录的上层目录或系统目录上",
    "unknown-cwd": "工作目录未知,相对路径无法确定指向哪里",
    "unparsable": "命令解析不了(引号不配对、嵌套太深或解析出错),按保守规则处理",
}


RULE_TEXT_EN = {
    "expansion": "the target contains a variable expansion, command substitution or backquote (an unquoted $ or backquote)",
    "tilde": "the target starts with ~",
    "protected-path": "the target is the home directory, a parent of it, or a system directory",
    "protected-glob": "a wildcard in the target lands on the home directory, a parent of it, or a system directory",
    "unknown-cwd": "the working directory is unknown, so a relative path cannot be resolved",
    "unparsable": "the command cannot be parsed (unbalanced quotes, nesting too deep or a parse error); the conservative rule applies",
}


def use_english():
    """English text only when the environment variable RM_GUARD_LANG is exactly 'en'."""
    return os.environ.get("RM_GUARD_LANG") == "en"


def build_reason(rule, target, english=None):
    if english is None:
        english = use_english()
    shown = target.replace("\r", " ").replace("\n", " ")[:200]
    if english:
        lines = [
            "Blocked: this command would recursively delete a path that cannot be determined before it runs, or that lands on the home directory or a system directory.",
            "Matched target: " + shown,
            "Matched condition: " + RULE_TEXT_EN.get(rule, rule),
            "rule=" + rule,
        ]
        if rule == "expansion":
            lines.append('Each Bash tool call starts a new shell, so a variable set in an earlier call is not set in this one; '
                         'an unset variable expands to empty, and "$X/sub" becomes "/sub".')
        lines.extend([
            "How to fix:",
            "1. Write the full literal path, and run ls -ld <path> first to confirm it is the one to delete.",
            '2. Create, use and delete a temporary directory in the same command: d=$(mktemp -d) && ... && rm -rf "$d"',
            "3. To delete a whole directory under the home directory or a system directory, ask the user to run it in their own terminal.",
        ])
        return "\n".join(lines)
    lines = [
        "已拒绝:这条命令会递归删除一个执行前无法确定、或落在家目录 / 系统目录上的路径。",
        "命中的目标: " + shown,
        "命中的条件: " + RULE_TEXT.get(rule, rule),
        "rule=" + rule,
    ]
    if rule == "expansion":
        lines.append('每次 Bash 工具调用都是新的 shell,上一次调用里设的变量这次不存在;'
                     '没设的变量展开成空,"$X/sub" 会变成 "/sub"。')
    lines.extend([
        "改法:",
        "1. 写出完整的字面路径,先 ls -ld <路径> 确认是要删的。",
        '2. 临时目录在同一条命令里建、用、删:d=$(mktemp -d) && … && rm -rf "$d"',
        "3. 确实要删家目录下的整个目录或系统目录:请使用者在自己的终端里运行。",
    ])
    return "\n".join(lines)


def _close_of(text, i):
    """Index of the ')' closing a '$(' whose body starts at i, or -1."""
    try:
        return _match_paren(text, i)
    except Exception:
        depth = 1
        n = len(text)
        while i < n:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1


def mask_substitutions(text):
    """Replace the content of $( ) and backquote substitutions with a placeholder."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "$" and text.startswith("$(", i):
            j = _close_of(text, i + 2)
            out.append("$(…)")
            if j < 0:
                break
            i = j + 1
        elif c == "`":
            j = i + 1
            while j < n and text[j] != "`":
                j += 2 if text[j] == "\\" else 1
            out.append("`…`")
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def write_log(rule, target):
    try:
        os.makedirs(os.path.dirname(LOG_PATH), mode=0o700, exist_ok=True)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        shown = mask_substitutions(target).replace("\r", " ").replace("\n", " ")[:200]
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(LOG_PATH, flags, 0o600)
        try:
            try:
                os.fchmod(fd, 0o600)
            except Exception:
                pass
            os.write(fd, ("%s\t%s\t%s\n" % (stamp, rule, shown)).encode("utf-8", "replace"))
        finally:
            os.close(fd)
    except Exception:
        pass


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        obj = json.loads(raw)
    except Exception:
        return 0
    if not isinstance(obj, dict):
        return 0
    ti = obj.get("tool_input")
    if not isinstance(ti, dict):
        return 0
    command = ti.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0
    cwd = obj.get("cwd")
    if not isinstance(cwd, str):
        cwd = None
    try:
        res = judge(command, cwd)
    except Exception:
        res = ("unparsable", command[:200])
    if res is None:
        return 0
    rule, target = res
    try:
        reason = build_reason(rule, str(target))
    except Exception:
        reason = ("Blocked: the target of the recursive delete cannot be determined.\nrule=" if use_english()
                  else "已拒绝:递归删除的目标无法确定。\nrule=") + str(rule)
    write_log(rule, str(target))
    try:
        out = json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}},
                         ensure_ascii=False)
        sys.stdout.buffer.write((out + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    except Exception:
        pass
    try:
        sys.stderr.buffer.write((reason + "\n").encode("utf-8"))
        sys.stderr.buffer.flush()
    except Exception:
        pass
    return 2


if __name__ == "__main__":
    sys.exit(main())
