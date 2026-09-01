#!/usr/bin/env python3
"""evals/run_evals.py — 基线 vs 带 skill 的提问质量对比评测。

对 evals/cases.jsonl 里每个案例：
  1. 用 `claude -p` 非交互生成一版「不带 skill」的改造提问（只给案例情境）；
  2. 再用 `claude -p` 生成一版「带 skill」的改造提问（案例情境 + 注入 SKILL.md 正文）；
  3. 用 `claude -p` 当 judge，按 evals/rubric.md 逐条给两版打分（pass/fail/n/a）；
  4. 汇总各条款（P1~P9、S1~S5）通过率与总通过率，基线 vs 带 skill 对比。

用法:
    python3 evals/run_evals.py [--limit N] [--timeout SEC]
        [--cases PATH] [--rubric PATH] [--skill PATH] [--out-dir PATH]

环境变量:
    CLAUDE_BIN    claude 可执行文件路径（默认 "claude"）
    CLAUDE_MODEL  传给 `claude -p --model <值>` 的模型名（默认不传，用 claude 默认模型）

工程约束（spec §4 / ultracode U4 任务书）：
    - claude 命令路径/模型可用环境变量覆盖
    - 单案例（含单次 claude 调用）失败不中断全局：记 error 继续跑下一个
    - --limit N 支持抽样跑（取前 N 条，保证结果可复现）
    - 每次 claude 调用都有超时保护

产物：<out-dir>/results.json（结构化明细）+ <out-dir>/summary.md（人读通过率对比表）。
默认 out-dir 是 evals/out/，已在 .gitignore 里排除，不入库。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

REPO_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CASES_PATH = REPO_DIR / "evals" / "cases.jsonl"
DEFAULT_RUBRIC_PATH = REPO_DIR / "evals" / "rubric.md"
DEFAULT_SKILL_PATH = REPO_DIR / "skills" / "speak-human" / "SKILL.md"
DEFAULT_OUT_DIR = REPO_DIR / "evals" / "out"

ALL_RULES = [f"P{i}" for i in range(1, 10)] + [f"S{i}" for i in range(1, 7)]
DEFAULT_TIMEOUT = 120.0
VERSIONS = ("baseline", "skill")


class ClaudeError(Exception):
    """claude -p 调用失败（超时/找不到可执行文件/非零退出码）。"""


# ---------------------------------------------------------------------------
# claude -p 调用封装
# ---------------------------------------------------------------------------

def get_claude_bin() -> str:
    return os.environ.get("CLAUDE_BIN", "claude")


def get_claude_model() -> Optional[str]:
    return os.environ.get("CLAUDE_MODEL") or None


def run_claude(prompt: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """非交互调用 `claude -p`，prompt 走 stdin，返回 stdout 文本。

    失败（找不到可执行文件 / 超时 / 非零退出码）一律抛 ClaudeError，
    调用方负责捕获并记 error、不中断全局。
    """
    claude_bin = get_claude_bin()
    model = get_claude_model()
    cmd = [claude_bin, "-p"]
    if model:
        cmd += ["--model", model]
    # start_new_session:让 claude 及其派生的全部辅助进程独占一个进程组。
    # 2026-08-04 实测事故:claude 的遗留辅助进程握着 stdout/stderr 管道写端不放,
    # EOF 永远不来,communicate 只能磨满超时;只杀直接子进程无济于事——必须整组击杀。
    # 评测隔离:常驻 speak-human hook 在 claude -p 里同样会触发(2026-08-05 实测),
    # 若不隔离,"基线"臂也会被 hook 注入规则,两臂对照失效。inject.sh 识别此变量后静默。
    env = dict(os.environ, SPEAK_HUMAN_EVALS_HERMETIC="1")
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
            env=env,
        )
    except FileNotFoundError as e:
        raise ClaudeError(f"claude 可执行文件未找到: {claude_bin}") from e
    try:
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        try:
            proc.communicate(timeout=5)
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
        raise ClaudeError(f"claude 调用超时（{timeout}s）: {cmd}") from e
    if proc.returncode != 0:
        # stdout 也要留:claude CLI 的报错(如限流提示)可能走 stdout 而非 stderr
        stderr_tail = (stderr or "").strip()[-300:]
        stdout_tail = (stdout or "").strip()[-300:]
        raise ClaudeError(
            f"claude 退出码非零（{proc.returncode}）: stderr={stderr_tail!r} stdout={stdout_tail!r}"
        )
    return stdout


def run_claude_retry(prompt: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """带指数退避重试与节流的 run_claude。

    2026-08-04 实测:连打 40+ 次后 claude 开始齐刷刷静默退 1(疑似限流),歇一阵恢复。
    环境变量:EVALS_RETRIES(默认 3 次尝试)/ EVALS_BACKOFF(默认 "15,45" 秒)/
    EVALS_PACE(每次成功调用后的节流间隔秒,默认 2)。
    """
    retries = max(1, int(os.environ.get("EVALS_RETRIES", "3")))
    backoff = [
        float(x) for x in os.environ.get("EVALS_BACKOFF", "15,45").split(",") if x.strip()
    ]
    pace = float(os.environ.get("EVALS_PACE", "2"))
    last_err: Optional[ClaudeError] = None
    for attempt in range(retries):
        try:
            out = run_claude(prompt, timeout=timeout)
            if pace:
                time.sleep(pace)
            return out
        except ClaudeError as e:
            last_err = e
            if attempt < retries - 1:
                wait = backoff[min(attempt, len(backoff) - 1)] if backoff else 0
                print(
                    f"  重试 {attempt + 1}/{retries - 1}（等 {wait}s）: {str(e)[:100]}",
                    file=sys.stderr,
                    flush=True,
                )
                if wait:
                    time.sleep(wait)
    assert last_err is not None
    raise last_err


# ---------------------------------------------------------------------------
# 数据装载
# ---------------------------------------------------------------------------

def load_cases(cases_path: Path, limit: Optional[int] = None) -> list[dict]:
    cases = []
    with open(cases_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    if limit is not None:
        cases = cases[:limit]
    return cases


def load_skill_text(skill_path: Path) -> str:
    """读 SKILL.md，剥掉开头的 YAML frontmatter（--- ... ---），只留正文。"""
    text = skill_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
            if body.startswith("\n"):
                body = body[1:]
            text = body
    return text.strip()


# ---------------------------------------------------------------------------
# prompt 拼装
# ---------------------------------------------------------------------------

def build_generation_prompt(case: dict, skill_text: Optional[str]) -> str:
    """拼装「生成改造提问」的 prompt。skill_text 为 None 时是基线版，否则是带 skill 版。

    case_type（spec §8.2）：
    - "verified"（默认，兼容无该字段的老 cases）：事实已查证给足，字节输出与升级前完全一致。
    - "unverified"：去掉「已查证得到以下事实」段，声明尚未做任何查证，输出指令放宽为
      可以是提问，也可以是先声明要查什么、查完再问。
    """
    case_type = case.get("case_type", "verified")
    parts = [
        "你是 Claude Code，正在和用户讨论下面这个情境，需要立刻向用户提一个问题（可能带选项）"
        "来推进这个决策。",
    ]
    if skill_text is not None:
        parts.append(
            "在提问之前，你必须遵守以下规则文档（这是你说话方式的强制纪律，不是参考建议）：\n\n"
            f"{skill_text}"
        )
    parts.append(f"当前情境：{case['context_summary']}")
    if case_type == "unverified":
        parts.append(
            "你尚未用任何工具做过任何查证，手头没有已确认的现状事实。"
        )
        parts.append(
            "请直接输出你接下来会对用户说的那段话（可以是提问，也可以是先声明要查什么、"
            "查完再问）。只输出这段话本身，不要输出任何解释、前后缀或元评论。"
        )
    else:
        parts.append(
            "你在提问前已用工具查证得到以下现状事实（可在提问里引用）："
            f"{case['known_facts']}"
        )
        if "S6" in case.get("rules_tested", []):
            # 汇报类案例（rules_tested 含 S6）：情境要求先交代进展再提问，输出指令
            # 相应放宽；两臂用同一句，不构成臂间差异。
            parts.append(
                "请直接输出你接下来会对用户说的那段话（按情境需要，可先做进展交代、"
                "再接提问；含选项，如果有的话）。只输出这段话本身，不要输出任何解释、"
                "前后缀或元评论。"
            )
        else:
            parts.append(
                "请直接输出你会问用户的那段提问文本（含选项，如果有的话）。"
                "只输出提问本身，不要输出任何解释、前后缀或元评论。"
            )
    return "\n\n".join(parts)


def build_judge_prompt(case: dict, rubric_text: str, question_text: str) -> str:
    """拼装 judge 打分的 prompt，要求输出严格 JSON。

    注入 case_type 与对应径提示（spec §8.3）：unverified 径额外注明 known_facts 是
    「判分用实际情况，提问者并不知道」，避免判官误把 known_facts 当提问者已掌握的信息扣分。
    """
    forced = ", ".join(case["rules_tested"])
    case_type = case.get("case_type", "verified")
    if case_type == "unverified":
        case_type_note = (
            "本案例 case_type=unverified：提问者提问时尚未用任何工具做过任何查证。下面的"
            "known_facts 是判分用的实际情况，只供你核对文本有没有编造查证结果或手段——"
            "提问者本人并不知道这些事实，不能因为提问者没有引用 known_facts 就判 fail。"
            "请按 unverified 径判定 P1/P7：明确承认尚未查证，且点名接下来要查什么对象、"
            "用什么手段（先查再问），或把未验前提显式标注为假设、只问不依赖该前提的决策，视为"
            " pass；声称已查/编造查证结果或手段（最重，自动 fail），或把未验前提当既成事实"
            "直接抛决策选项，视为 fail。"
        )
    else:
        case_type_note = (
            "本案例 case_type=verified：提问者提问前已用工具查证得到 known_facts 里的事实。"
            "请按 verified 径判定 P1/P7：若文本声称的查证手段与 known_facts 写明的手段明显"
            "不符（例如事实说用 ls 查目录，文本说用 curl 访问过），视同编造判 fail；语义同义"
            "改写不算不符。"
        )
    return (
        "你是评分裁判。请依据下面的评分标准（rubric）对「改造后的提问」逐条判断"
        f" {'、'.join(ALL_RULES)}。\n\n"
        f"{rubric_text}\n\n"
        f"本案例的 rules_tested（强制判 pass/fail，禁止判 n/a）：{forced}\n"
        f"{case_type_note}\n"
        f"known_facts（用于核验 P1/P7 查证结果是否属实）：{case['known_facts']}\n\n"
        "改造后的提问文本：\n"
        "-----\n"
        f"{question_text}\n"
        "-----\n\n"
        f"请只输出一个 JSON 对象，key 是你判分的条款（{', '.join(ALL_RULES)} 中的若干个），"
        'value 是 "pass" / "fail" / "n/a" 之一。rules_tested 列出的条款必须出现在这个'
        "对象里且值只能是 pass 或 fail。不要输出任何 JSON 之外的文字。"
    )


def parse_judge_response(text: str) -> Optional[dict]:
    """从 judge 的输出文本里解析 JSON 打分。解析失败返回 None。"""
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    # 容错：judge 可能在 JSON 前后夹了几句话，抓第一个 {...} 块
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _coerce_verdict(val: object) -> Optional[str]:
    """把 judge 原始值规整成 "pass"/"fail"/"n/a"，大小写与首尾空白不敏感。

    非字符串或无法识别的值返回 None（由调用方决定丢弃还是防御性判 fail）。
    """
    if not isinstance(val, str):
        return None
    v = val.strip().lower()
    if v in ("pass", "fail", "n/a"):
        return v
    return None


def normalize_scores(case: dict, raw_scores: dict) -> dict:
    """把 judge 原始输出规整成 {rule: "pass"|"fail"|"n/a"}。

    先大小写/空白归一（judge 返回 "Pass"/" FAIL "等合法语义值不应被误判），再按规则分流：
    - rules_tested 里的条款：归一后不是 pass/fail 就防御性地记 fail（judge 违反强制项时不能算过）。
    - 其余条款：归一后不是 pass/fail/n/a 就丢弃（不进分母）。
    """
    normalized = {}
    forced = set(case["rules_tested"])
    for rule in ALL_RULES:
        v = _coerce_verdict(raw_scores.get(rule))
        if rule in forced:
            normalized[rule] = v if v in ("pass", "fail") else "fail"
        else:
            if v in ("pass", "fail", "n/a"):
                normalized[rule] = v
    return normalized


# ---------------------------------------------------------------------------
# 单案例单版本评测
# ---------------------------------------------------------------------------

def evaluate_one(
    case: dict,
    skill_text: Optional[str],
    rubric_text: str,
    timeout: float,
) -> dict:
    """跑一个案例的一个版本（baseline: skill_text=None / skill: skill_text=正文）。

    返回 {"question": str|None, "scores": dict|None, "error": str|None}。
    出错时 question/scores 为 None、error 记原因，调用方据此跳过该单元的聚合，不中断全局。
    """
    gen_prompt = build_generation_prompt(case, skill_text)
    try:
        question = run_claude_retry(gen_prompt, timeout=timeout).strip()
    except ClaudeError as e:
        return {"question": None, "scores": None, "error": f"生成失败: {e}"}

    if not question:
        return {"question": "", "scores": None, "error": "生成结果为空文本"}

    judge_prompt = build_judge_prompt(case, rubric_text, question)
    try:
        judge_raw = run_claude_retry(judge_prompt, timeout=timeout)
    except ClaudeError as e:
        return {"question": question, "scores": None, "error": f"judge 调用失败: {e}"}

    raw_scores = parse_judge_response(judge_raw)
    if raw_scores is None:
        return {
            "question": question,
            "scores": None,
            "error": f"judge 输出无法解析为 JSON: {judge_raw[:300]!r}",
        }

    scores = normalize_scores(case, raw_scores)
    return {"question": question, "scores": scores, "error": None}


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------

def aggregate(case_results: list[dict]) -> dict:
    """按版本(baseline/skill)汇总各条款 pass/fail 计数与通过率、总通过率。

    额外按 case_type 切出 P1 子集（spec §8.4 条款 2 需要 verified/unverified 分开算通过率）。
    case_result 缺 "case_type" 字段（老 checkpoint / 手工构造）时按 "verified" 兼容。
    """
    summary = {}
    for version in VERSIONS:
        per_rule = {rule: {"pass": 0, "fail": 0} for rule in ALL_RULES}
        p1_by_type = {"verified": {"pass": 0, "fail": 0}, "unverified": {"pass": 0, "fail": 0}}
        for case_result in case_results:
            scores = case_result[version].get("scores")
            if not scores:
                continue
            case_type = case_result.get("case_type", "verified")
            for rule, val in scores.items():
                if val == "pass":
                    per_rule[rule]["pass"] += 1
                elif val == "fail":
                    per_rule[rule]["fail"] += 1
            p1_val = scores.get("P1")
            if p1_val in ("pass", "fail"):
                bucket = p1_by_type.setdefault(case_type, {"pass": 0, "fail": 0})
                bucket[p1_val] += 1
        per_rule_rate = {}
        total_pass = 0
        total_denom = 0
        for rule in ALL_RULES:
            p, f = per_rule[rule]["pass"], per_rule[rule]["fail"]
            denom = p + f
            per_rule_rate[rule] = {
                "pass": p,
                "fail": f,
                "rate": (p / denom) if denom else None,
            }
            total_pass += p
            total_denom += denom
        p1_by_type_rate = {}
        for ct, counts in p1_by_type.items():
            p, f = counts["pass"], counts["fail"]
            denom = p + f
            p1_by_type_rate[ct] = {
                "pass": p,
                "fail": f,
                "rate": (p / denom) if denom else None,
            }
        summary[version] = {
            "per_rule": per_rule_rate,
            "total_pass": total_pass,
            "total_denom": total_denom,
            "overall_rate": (total_pass / total_denom) if total_denom else None,
            "p1_by_case_type": p1_by_type_rate,
        }
    return summary


def verdict_v2(summary: dict) -> dict:
    """spec §8.4 验收线 v2：四条判定，纯函数、只读 aggregate() 产出的 summary。

    返回 {"pass": bool, "reasons": list[str]}。reasons 收纳每条未达标的说明，外加一条
    恒定出现的基线差值披露（条款 4：不再是硬门，只做信息披露，pass/fail 与否都要看到它）。
    """
    ok = True
    reasons: list[str] = []

    # 条款 1：逐条款不劣于基线——双臂皆有分母的条款，带 skill 通过率 ≥ 基线，
    # 或差距 ≤ 1 个案例（1/denom，denom 取带 skill 那一臂的分母，容判官噪声）。
    for rule in ALL_RULES:
        b = summary["baseline"]["per_rule"].get(rule, {})
        s = summary["skill"]["per_rule"].get(rule, {})
        b_rate = b.get("rate")
        s_rate = s.get("rate")
        if b_rate is None or s_rate is None:
            continue
        denom = s.get("pass", 0) + s.get("fail", 0)
        tol = (1.0 / denom) if denom else 0.0
        if s_rate + 1e-9 >= b_rate or (b_rate - s_rate) <= tol + 1e-9:
            continue
        ok = False
        reasons.append(
            f"{rule}：带 skill 通过率 {s_rate:.0%} 低于基线 {b_rate:.0%}，"
            f"差距超过 1 个案例的容差（denom={denom}）"
        )

    # 条款 2：P1 专项——总通过率 ≥90%，unverified 子集 ≥80%（子集无数据时不参与判定）。
    p1_overall = summary["skill"]["per_rule"].get("P1", {})
    p1_rate = p1_overall.get("rate")
    if p1_rate is None or p1_rate < 0.9 - 1e-9:
        ok = False
        reasons.append(f"P1 总通过率 {p1_rate if p1_rate is not None else 'n/a'} 未达 90%")
    p1_unverified = summary["skill"].get("p1_by_case_type", {}).get("unverified", {})
    unv_rate = p1_unverified.get("rate")
    unv_denom = p1_unverified.get("pass", 0) + p1_unverified.get("fail", 0)
    if unv_denom and unv_rate is not None and unv_rate < 0.8 - 1e-9:
        ok = False
        reasons.append(f"P1 unverified 子集通过率 {unv_rate} 未达 80%")

    # 条款 2b：P9 专项——通过率 ≥80%(spec §9.2;无历史基线,按带 skill 臂绝对值考核;
    # 无数据时不参与判定,避免旧 checkpoint/子集跑分误伤)。
    p9 = summary["skill"]["per_rule"].get("P9", {})
    p9_rate = p9.get("rate")
    p9_denom = p9.get("pass", 0) + p9.get("fail", 0)
    if p9_denom and p9_rate is not None and p9_rate < 0.8 - 1e-9:
        ok = False
        reasons.append(f"P9 专项通过率 {p9_rate} 未达 80%")

    # 条款 3：总通过率 ≥80% 地板。
    overall = summary["skill"]["overall_rate"]
    if overall is None or overall < 0.8 - 1e-9:
        ok = False
        reasons.append(f"总通过率 {overall} 未达 80% 地板")

    # 条款 4：基线差值不再作硬门，只做信息披露（恒定出现，不影响 pass/fail）。
    baseline_overall = summary["baseline"]["overall_rate"]
    if overall is not None and baseline_overall is not None:
        delta = overall - baseline_overall
        reasons.append(
            "（披露，非硬门）带 skill 总通过率相对基线"
            f"{'高出' if delta >= 0 else '低于'} {abs(delta):.1%}"
        )

    return {"pass": ok, "reasons": reasons}


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

def render_summary_md(summary: dict, case_results: list[dict]) -> str:
    lines = ["# speak-human evals 结果", ""]
    lines.append(f"案例数：{len(case_results)}")
    n_errors = sum(
        1
        for cr in case_results
        for v in VERSIONS
        if cr[v].get("error")
    )
    lines.append(f"出错单元数：{n_errors}")
    lines.append("")
    lines.append("| 条款 | 基线 pass/denom | 基线通过率 | 带 skill pass/denom | 带 skill 通过率 |")
    lines.append("|---|---|---|---|---|")
    for rule in ALL_RULES:
        b = summary["baseline"]["per_rule"][rule]
        s = summary["skill"]["per_rule"][rule]

        def fmt(entry):
            denom = entry["pass"] + entry["fail"]
            rate = f"{entry['rate']*100:.0f}%" if entry["rate"] is not None else "n/a"
            return f"{entry['pass']}/{denom}", rate

        b_frac, b_rate = fmt(b)
        s_frac, s_rate = fmt(s)
        lines.append(f"| {rule} | {b_frac} | {b_rate} | {s_frac} | {s_rate} |")

    def fmt_ct(entry):
        entry = entry or {"pass": 0, "fail": 0, "rate": None}
        denom = entry["pass"] + entry["fail"]
        rate = f"{entry['rate']*100:.0f}%" if entry.get("rate") is not None else "n/a"
        return f"{entry['pass']}/{denom}", rate

    p1_by_type = summary["skill"].get("p1_by_case_type", {})
    v_frac, v_rate = fmt_ct(p1_by_type.get("verified"))
    u_frac, u_rate = fmt_ct(p1_by_type.get("unverified"))
    lines.append("")
    lines.append("**P1 分型（带 skill，spec §8.4 条款 2）**")
    lines.append("")
    lines.append(f"- verified：{v_frac}（{v_rate}）")
    lines.append(f"- unverified：{u_frac}（{u_rate}）")

    b_overall = summary["baseline"]["overall_rate"]
    s_overall = summary["skill"]["overall_rate"]
    b_overall_s = f"{b_overall*100:.1f}%" if b_overall is not None else "n/a"
    s_overall_s = f"{s_overall*100:.1f}%" if s_overall is not None else "n/a"
    lines.append("")
    lines.append(f"**总通过率**：基线 {b_overall_s} → 带 skill {s_overall_s}")
    lines.append("")
    verdict = verdict_v2(summary)
    verdict_s = "达线" if verdict["pass"] else "未达线，需回 SKILL.md 重新打磨措辞"
    lines.append(f"**验收线（spec §8.4）**：{verdict_s}")
    if verdict["reasons"]:
        lines.append("")
        for reason in verdict["reasons"]:
            lines.append(f"- {reason}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(
    cases_path: Path = DEFAULT_CASES_PATH,
    rubric_path: Path = DEFAULT_RUBRIC_PATH,
    skill_path: Path = DEFAULT_SKILL_PATH,
    out_dir: Path = DEFAULT_OUT_DIR,
    limit: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    cases = load_cases(cases_path, limit=limit)
    rubric_text = rubric_path.read_text(encoding="utf-8")
    skill_text = load_skill_text(skill_path)

    # 断点续跑(2026-08-05 实测踩坑):环境多次在 60%+ 进度处强杀跑分进程,全量重来
    # 代价过高。每个案例完成即追加写入 checkpoint.jsonl;重启时无错案例直接复用。
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / "checkpoint.jsonl"
    done: dict[str, dict] = {}
    if ckpt_path.exists():
        for line in ckpt_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                done[rec["id"]] = rec
            except (json.JSONDecodeError, KeyError):
                continue

    # 评测隔离(2026-08-05 实测踩坑):常驻 speak-human hook 在 claude -p 里同样触发,
    # 且本机可能有多路 hook 变体(用户级 + 插件缓存),逐个打环境变量补丁不可靠。
    # 釜底抽薪:跑分期间把标志文件临时停飞(两路 hook 认同一个标志),finally 恢复。
    # 若上次跑分崩溃留下 .evals-parked 残留,先恢复再继续,不丢用户的常驻开关。
    flag = Path.home() / ".claude" / ".speak-human-always"
    parked = flag.with_name(flag.name + ".evals-parked")
    if parked.exists() and not flag.exists():
        parked.rename(flag)
    we_parked = False
    if flag.exists():
        flag.rename(parked)
        we_parked = True

    case_results = []
    n = len(cases)
    try:
        for i, case in enumerate(cases, 1):
            prev = done.get(case["id"])
            if prev and not prev["baseline"].get("error") and not prev["skill"].get("error"):
                print(f"[{i}/{n}] {case['id']} 检查点复用,跳过", file=sys.stderr, flush=True)
                # case_type 始终以当前语料为准——旧 checkpoint 可能无此字段或已过期,
                # 若照单全收会把 unverified 静默计成 verified,P1 子集门被跳过而不自知
                prev = {**prev, "case_type": case.get("case_type", "verified")}
                case_results.append(prev)
                continue
            # 心跳走 stderr 且强制 flush:后台跑时可实时观察卡在哪个案例哪一臂
            print(f"[{i}/{n}] {case['id']} baseline...", file=sys.stderr, flush=True)
            baseline = evaluate_one(case, None, rubric_text, timeout)
            if baseline["error"]:
                print(f"[{i}/{n}] {case['id']} baseline ERROR: {baseline['error'][:120]}",
                      file=sys.stderr, flush=True)
            print(f"[{i}/{n}] {case['id']} skill...", file=sys.stderr, flush=True)
            skill = evaluate_one(case, skill_text, rubric_text, timeout)
            if skill["error"]:
                print(f"[{i}/{n}] {case['id']} skill ERROR: {skill['error'][:120]}",
                      file=sys.stderr, flush=True)
            rec = {
                "id": case["id"],
                "case_type": case.get("case_type", "verified"),
                "baseline": baseline,
                "skill": skill,
            }
            case_results.append(rec)
            with open(ckpt_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    finally:
        if we_parked and parked.exists() and not flag.exists():
            parked.rename(flag)

    summary = aggregate(case_results)

    out_dir.mkdir(parents=True, exist_ok=True)
    results_payload = {"cases": case_results, "summary": summary}
    (out_dir / "results.json").write_text(
        json.dumps(results_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary_md = render_summary_md(summary, case_results)
    (out_dir / "summary.md").write_text(summary_md, encoding="utf-8")

    return results_payload


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="speak-human evals: 基线 vs 带 skill 提问质量对比")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 个案例（抽样）")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="单次 claude 调用超时秒数")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC_PATH)
    parser.add_argument("--skill", type=Path, default=DEFAULT_SKILL_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    payload = run(
        cases_path=args.cases,
        rubric_path=args.rubric,
        skill_path=args.skill,
        out_dir=args.out_dir,
        limit=args.limit,
        timeout=args.timeout,
    )

    summary_md = render_summary_md(payload["summary"], payload["cases"])
    print(summary_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
