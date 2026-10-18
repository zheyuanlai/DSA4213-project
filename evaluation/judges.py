"""AI judge runners for the evaluation extension: provenance, caching, budget and leakage control.

Two model families give independent readings (protocol §3):

* Judge A / adjudicator: OpenAI GPT-5.6 (``gpt-5.6-sol``) through ``codex exec`` (ephemeral, read-only sandbox,
  empty working directory, JSON-schema output). Its event log is checked for shell commands.
* Judge B: Anthropic Claude Sonnet 5.5 through ``claude -p`` with every tool disabled, no settings, MCP or
  session persistence, a custom system prompt and JSON-schema output. Its list-price cost is capped.

Every call is cached by sha256 of (backend, model, settings, prompt name and hash, schema, filled prompt), so a
re-run never repeats a paid call. Raw records keep the model ID, prompt hash, settings, usage, cost, timestamps,
the raw response and the parsed JSON. A ``mock`` backend makes the pipeline testable offline.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
PROMPT_DIR = ROOT / "annotation" / "ai_extended" / "prompts"
RAW_DIR = ROOT / "annotation" / "ai_extended" / "raw"
CLAUDE_BUDGET_USD = 6.50
CLAUDE_PER_CALL_CAP_USD = 0.75  # verification calls (largest outputs)
CLAUDE_STAGE_CAP_USD = {"verify": 0.75}  # other stages (coverage, alignment, checklist review) are small
CLAUDE_DEFAULT_STAGE_CAP_USD = 0.25


def claude_call_cap(stage: str) -> float:
    return CLAUDE_STAGE_CAP_USD.get(stage, CLAUDE_DEFAULT_STAGE_CAP_USD)


# ----------------------------------------------------------------------------- judges
@dataclass(frozen=True)
class JudgeSpec:
    name: str  # "A", "B", "ADJ"
    backend: str  # codex | claude | mock
    model: str
    settings: tuple[tuple[str, str], ...] = ()

    @property
    def settings_dict(self) -> dict[str, str]:
        return dict(self.settings)


JUDGE_A = JudgeSpec("A", "codex", "gpt-5.6-sol", (("model_reasoning_effort", "high"),))
JUDGE_B = JudgeSpec("B", "claude", "claude-sonnet-5-5", ())
JUDGE_B_LITE = JudgeSpec("B", "claude", "claude-haiku-5-5", ())
ADJUDICATOR = JudgeSpec("ADJ", "codex", "gpt-5.6-sol", (("model_reasoning_effort", "high"),))
# Judge C (protocol amendment 12): a third, Alibaba-family judge through the project's own OpenRouter client and
# cost ledger. DeepSeek models are excluded as judges because a DeepSeek model is the system being evaluated.
JUDGE_C = JudgeSpec("C", "openrouter", "qwen/qwen3.7-plus", (("temperature", "0"), ("seed", "4213"), ("reasoning", "off")))
OPENROUTER_STAGE = "eval_ext"
OPENROUTER_STAGE_CAP_USD = 1.78  # remaining room under the extension's $7 external-inference cap
OPENROUTER_MAX_TOKENS = 24000


def judge_b_for(family: str, stage: str) -> JudgeSpec:
    """Judge B model rule fixed after the pilot (protocol §11, amendment 5): Sonnet 5.5 for real-paper and
    long-diagnostic verification and coverage; Haiku 5.5 for synthetic verification and for all alignment."""
    return JUDGE_B_LITE if family == "synthetic" or stage == "align" else JUDGE_B


def load_prompt(name: str) -> tuple[str, str]:
    text = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode()).hexdigest()


def fill(template: str, **parts: str) -> str:
    out = template
    for k, v in parts.items():
        out = out.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if left:
        raise ValueError(f"unfilled placeholders {left}")
    return out


# ----------------------------------------------------------------------------- leakage control
STRICT_PATTERNS = [
    (re.compile(r"\bC[1-7]\b"), "condition label"),
    (re.compile(r"\b(?:SIG|ROB|GEN|CON|EFF|CIT|NUM|NEG)-p\d[ab]\b"), "synthetic case id"),
    (re.compile(r"\bLONG-\d{2}\b"), "diagnostic case id"),
    (re.compile(r"\b(?:primary_v1|real_v1|real_v2|diag_v2|h2diag_v1|dev_pilot\d)\b"), "run tag"),
    (re.compile(r"private/|condition_mapping|case_alias_map|test_gold|diagnostic_gold"), "private path"),
    (re.compile(r"gold_level|gold_decision|focal_proposition|level_descriptors|pair_contrast|forbidden_claims"),
     "gold field"),
]
TEMPLATE_WORDS = re.compile(
    r"\b(?:verifier|verified|verification|draft|baseline|condition|outline|writer|reviewer|revis(?:ed|ion)|"
    r"strengthen|weaken|adaptive|scripted|agent|deepseek|gold)\b", re.I)


class LeakageError(RuntimeError):
    pass


def check_leakage(prompt: str, data_segments: list[str], forbidden_texts: list[str] = ()) -> None:
    """Refuse a judge prompt that could reveal conditions, lineage or gold.

    ``data_segments`` are the package rendering (first element, by convention) and model-written passages/claims;
    they are model-visible data and may legitimately contain words such as "baseline". Strict patterns (condition
    labels, case IDs, run tags, private paths, gold fields) are checked on everything except the package, including
    model-written text; lineage words only on the instructions and structure we wrote."""
    package = data_segments[0] if data_segments else ""
    outside_package = prompt.replace(package, " ") if package else prompt
    for pat, what in STRICT_PATTERNS:
        m = pat.search(outside_package)
        if m:
            raise LeakageError(f"{what} in judge prompt: {m.group(0)!r}")
    stripped = prompt
    for seg in sorted(set(s for s in data_segments if s), key=len, reverse=True):
        stripped = stripped.replace(seg, " ")
    m = TEMPLATE_WORDS.search(stripped)
    if m:
        raise LeakageError(f"lineage/condition word in judge prompt structure: {m.group(0)!r}")
    for t in forbidden_texts:
        t = (t or "").strip()
        if len(t) >= 25 and t[:60] in prompt:
            raise LeakageError(f"gold text in judge prompt: {t[:40]!r}")


# ----------------------------------------------------------------------------- schemas
def _obj(props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


def _arr(items: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": items}


def _enum(*vals: str) -> dict[str, Any]:
    return {"type": "string", "enum": list(vals)}


def _nullable(s: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [s, {"type": "null"}]}


STR = {"type": "string"}
CLAIM_TYPES = ("result_value", "comparison", "statistical_significance", "consistency_or_generality", "robustness",
               "generalization", "efficiency", "citation_attribution", "negative_or_null_result", "trend_or_tradeoff",
               "causal_or_mechanistic", "scope_or_caveat", "method_or_setup", "other")
NUMBER_ROLES = ("result", "derived", "statistical", "cited", "count_outcome", "setup")
LABELS = ("SUPPORTED", "OVERSTATED", "UNDERSTATED", "UNSUPPORTED", "NOT_VERIFIABLE")
ENTAILMENT = ("ENTAILED", "NOT_ENTAILED", "CONTRADICTED", "NA")
EXTRACTION_FLAGS = ("OK", "NOT_IN_TEXT", "NOT_ATOMIC", "DISTORTED")
COVERAGE = ("CORRECT", "INCORRECT", "ABSENT")
RELATIONS = ("UNCHANGED", "REWORDED", "MODIFIED", "DELETED")
DIRECTIONS = ("WEAKENED", "STRENGTHENED", "NUMBER_CHANGED", "SCOPE_CHANGED", "OTHER")
SOURCE_TYPES = ("cell", "test", "text", "none")
POLARITY = ("positive", "negative", "null", "mixed", "neutral")
KINDS = ("main_result", "comparison", "negative_or_null", "scope_limitation", "other")

MAPPING = {"source_type": _enum(*SOURCE_TYPES), "expression": _nullable(STR), "quote": _nullable(STR),
           "scale": {"type": "number"}}

SCHEMAS: dict[str, dict[str, Any]] = {
    "extract": _obj({"units": _arr(_obj({"unit_id": STR, "claims": _arr(_obj({
        "span": STR, "proposition": STR, "claim_type": _enum(*CLAIM_TYPES), "entities": _arr(STR),
        "metrics": _arr(STR), "datasets": _arr(STR), "qualifiers": _arr(STR),
        "numbers": _arr(_obj({"as_written": STR, "value": {"type": "number"}, "comparator": _enum("=", "<", "<=", ">", ">="),
                              "approximate": {"type": "boolean"}, "role": _enum(*NUMBER_ROLES), "unit": _nullable(STR)}))}))}))}),
    "verify": _obj({"claims": _arr(_obj({
        "claim_id": STR, "label": _enum(*LABELS), "entailment": _enum(*ENTAILMENT), "error_subtype": _nullable(STR),
        "evidence_ids": _arr(STR), "justification": STR, "confidence": _enum("low", "medium", "high"),
        "extraction_flag": _enum(*EXTRACTION_FLAGS), "numbers": _arr(_obj({"number_id": STR, **MAPPING}))}))}),
    "coverage": _obj({"judgments": _arr(_obj({"passage": STR, "item_id": STR, "status": _enum(*COVERAGE),
                                              "justification": STR}))}),
    "align": _obj({"pairs": _arr(_obj({"pair_id": STR, "x_claims": _arr(_obj({
        "claim_id": STR, "relation": _enum(*RELATIONS), "direction": _nullable(_enum(*DIRECTIONS)),
        "matched_y": _arr(STR)})), "added_y": _arr(STR)}))}),
    "checklist_build": _obj({
        "findings": _arr(_obj({"finding_id": STR, "description": STR, "polarity": _enum(*POLARITY), "kind": _enum(*KINDS),
                               "importance": _enum("core", "supporting"), "evidence_ids": _arr(STR)})),
        "numeric_facts": _arr(_obj({"fact_id": STR, "description": STR, "expression": STR, "value": {"type": "number"},
                                    "unit": _nullable(STR), "finding_id": _nullable(STR)}))}),
    "checklist_review": _obj({
        "item_reviews": _arr(_obj({"item_id": STR, "verdict": _enum("VALID", "UNSUPPORTED", "TRIVIAL"), "comment": STR})),
        "missing_core_findings": _arr(_obj({"description": STR, "polarity": _enum(*POLARITY), "kind": _enum(*KINDS),
                                            "evidence_ids": _arr(STR)}))}),
    "adjudicate_claims": _obj({"decisions": _arr(_obj({
        "item_id": STR, "label": _enum(*LABELS, "UNRESOLVED"), "entailment": _enum(*ENTAILMENT, "UNRESOLVED"),
        "extraction_valid": {"type": "boolean"},
        "numbers": _arr(_obj({"number_id": STR, "choice": _enum("1", "2", "own"), **MAPPING})),
        "rationale": STR, "evidence_ids": _arr(STR)}))}),
    "adjudicate_coverage": _obj({"decisions": _arr(_obj({"item_id": STR, "status": _enum(*COVERAGE, "UNRESOLVED"),
                                                         "rationale": STR}))}),
    "adjudicate_align": _obj({"decisions": _arr(_obj({
        "item_id": STR, "relation": _enum(*RELATIONS, "UNRESOLVED"), "direction": _nullable(_enum(*DIRECTIONS)),
        "matched_y": _arr(STR), "rationale": STR}))}),
}


# ----------------------------------------------------------------------------- backends
class JudgeError(RuntimeError):
    pass


def _codex_call(spec: JudgeSpec, prompt: str, schema: dict[str, Any], system: str) -> dict[str, Any]:
    work = Path(tempfile.mkdtemp(prefix="judge_a_"))
    try:
        (work / "schema.json").write_text(json.dumps(schema))
        cmd = ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-rules", "-s", "read-only",
               "-C", str(work), "-m", spec.model, "--output-schema", str(work / "schema.json"),
               "-o", str(work / "last.json"), "--json"]
        for k, v in spec.settings:
            cmd += ["-c", f'{k}="{v}"']
        cmd.append("-")
        t0 = time.time()
        proc = subprocess.run(cmd, input=system + "\n\n" + prompt, capture_output=True, text=True, timeout=3600,
                              cwd=work)
        dt = time.time() - t0
        events = [json.loads(l) for l in proc.stdout.splitlines() if l.strip().startswith("{")]
        usage = next((e.get("usage") for e in reversed(events) if e.get("type") == "turn.completed"), None)
        item_types = sorted({(e.get("item") or {}).get("type", "") for e in events if e.get("type") == "item.completed"})
        tool_use = [t for t in item_types if t not in ("agent_message", "reasoning", "")]
        raw = (work / "last.json").read_text() if (work / "last.json").exists() else ""
        if proc.returncode != 0 or not raw:
            raise JudgeError(f"codex exit {proc.returncode}: {proc.stderr[-500:]}")
        return {"raw_response": raw, "usage": usage, "cost_usd": None, "latency_s": round(dt, 1),
                "model_reported": spec.model, "model_report_source": "requested via -m (codex exec does not echo it)",
                "tool_use_detected": tool_use, "cli_version": _cli_version("codex")}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _claude_call(spec: JudgeSpec, prompt: str, schema: dict[str, Any], system: str,
                 cap: float = CLAUDE_PER_CALL_CAP_USD) -> dict[str, Any]:
    work = Path(tempfile.mkdtemp(prefix="judge_b_"))
    try:
        # Plain JSON text validated locally against the same schema: the CLI's --json-schema mode makes the
        # model emit the object twice (text + structured-output tool), doubling metered output tokens.
        cmd = ["claude", "-p", "--model", spec.model, "--tools", "", "--output-format", "json",
               "--no-session-persistence", "--setting-sources", "", "--strict-mcp-config",
               "--system-prompt", system, "--max-budget-usd", str(cap)]
        full = (prompt + "\n\n## Output format\nReturn exactly one JSON object, with no text before or after it, "
                "that validates against this JSON Schema:\n" + json.dumps(schema, separators=(",", ":")))
        t0 = time.time()
        proc = subprocess.run(cmd, input=full, capture_output=True, text=True, timeout=3600, cwd=work)
        dt = time.time() - t0
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise JudgeError(f"claude exit {proc.returncode}: {proc.stdout[-300:]} {proc.stderr[-300:]}") from e
        cost = out.get("total_cost_usd")
        if out.get("is_error"):
            raise JudgeError(f"claude error ({out.get('subtype')}): {str(out.get('result'))[:300]}", cost)
        text = out.get("result") or ""
        i, j = text.find("{"), text.rfind("}")
        if i < 0 or j < i:
            raise JudgeError(f"claude returned no JSON object: {text[:200]}", cost)
        models = sorted((out.get("modelUsage") or {}).keys())
        return {"raw_response": text[i:j + 1], "usage": out.get("usage"), "cost_usd": cost,
                "latency_s": round(dt, 1), "model_reported": ",".join(models), "model_report_source": "modelUsage",
                "tool_use_detected": [], "cli_version": _cli_version("claude"), "num_turns": out.get("num_turns")}
    finally:
        shutil.rmtree(work, ignore_errors=True)


_OR_CLIENT: dict[str, Any] = {}


def _openrouter_client(spec: JudgeSpec):
    """The project's OpenRouter client with its CostGuard: provider-reported cost is appended to the shared, secret-free
    ledger (outputs/cost_ledger.jsonl) and calls are refused beyond the project hard cap or the eval_ext stage cap."""
    if spec.model not in _OR_CLIENT:
        import yaml
        from src.cost_guard import CostGuard, Pricing
        from src.openrouter_client import OpenRouterClient
        budget = yaml.safe_load((ROOT / "configs" / "budget.yaml").read_text())
        guard = CostGuard(ROOT / "outputs" / "cost_ledger.jsonl", float(budget["hard_cap_usd"]),
                          {OPENROUTER_STAGE: OPENROUTER_STAGE_CAP_USD}, Pricing(0.32e-6, 1.28e-6), max_inflight=3)
        st = spec.settings_dict
        decoding = {"temperature": float(st.get("temperature", 0)), "seed": int(st.get("seed", 4213)),
                    "reasoning": {"enabled": st.get("reasoning", "off") != "off"}}
        _OR_CLIENT[spec.model] = OpenRouterClient(spec.model, {"require_parameters": True}, decoding, guard,
                                                  timeout_s=600.0, max_retries=2, app_title="DSA4213-project-eval-ext")
    return _OR_CLIENT[spec.model]


def _openrouter_call(spec: JudgeSpec, prompt: str, schema: dict[str, Any], system: str, item_key: str) -> dict[str, Any]:
    client = _openrouter_client(spec)
    rf = {"type": "json_schema", "json_schema": {"name": "judgement", "strict": True, "schema": schema}}
    t0 = time.time()
    try:
        res = client.chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                          role="eval_ext_judge", max_tokens=OPENROUTER_MAX_TOKENS, response_format=rf,
                          ctx={"stage": OPENROUTER_STAGE, "case_id": item_key, "condition": None,
                               "run_tag": "eval_ext_judge_C", "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16]})
    except Exception as e:  # BudgetExceeded, FatalAPIError, TransientAPIError
        raise JudgeError(f"openrouter: {type(e).__name__}: {str(e)[:300]}") from e
    text = res.content or ""
    i, j = text.find("{"), text.rfind("}")
    if i < 0 or j < i:
        raise JudgeError(f"openrouter returned no JSON (finish {res.finish_reason})", res.cost_usd)
    return {"raw_response": text[i:j + 1], "usage": res.usage, "cost_usd": res.cost_usd, "cost_source": res.cost_source,
            "latency_s": round(time.time() - t0, 1), "model_reported": spec.model,
            "model_report_source": f"requested; provider {res.provider}; generation {res.generation_id}",
            "tool_use_detected": [], "cli_version": "src/openrouter_client.py", "finish_reason": res.finish_reason}


def openrouter_spent(raw_dir: Optional[Path] = None) -> float:
    raw_dir = raw_dir or RAW_DIR
    total = 0.0
    for p in raw_dir.rglob("*.json"):
        try:
            rec = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        if rec.get("backend") == "openrouter":
            total += float(rec.get("cost_usd") or 0.0) + sum(float(a.get("cost_usd") or 0.0) for a in rec.get("failed_attempts", []))
    return total


_VERSIONS: dict[str, str] = {}


def _cli_version(tool: str) -> str:
    if tool not in _VERSIONS:
        try:
            _VERSIONS[tool] = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
        except Exception:  # noqa: BLE001
            _VERSIONS[tool] = "unknown"
    return _VERSIONS[tool]


MOCK_RESPONDERS: dict[str, Callable[[str, dict[str, Any]], dict[str, Any]]] = {}


# ----------------------------------------------------------------------------- cached runner
_LOCK = threading.Lock()
_RESERVED: list[float] = [0.0]


def claude_spent(raw_dir: Optional[Path] = None) -> float:
    raw_dir = raw_dir or RAW_DIR
    total = 0.0
    for p in raw_dir.rglob("*.json"):
        try:
            rec = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        if rec.get("backend") == "claude":
            total += float(rec.get("cost_usd") or 0.0)
            total += sum(float(a.get("cost_usd") or 0.0) for a in rec.get("failed_attempts", []))
    return total


USED_PATHS: set[Path] = set()  # raw records used by the current process (for separating superseded pilots)


def write_used(tag: str, raw_dir: Optional[Path] = None) -> None:
    raw_dir = raw_dir or RAW_DIR
    used = sorted(str(p.relative_to(raw_dir)) for p in USED_PATHS if raw_dir in p.parents)
    if used:
        out = raw_dir / "used" / f"{tag}.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        old = set(out.read_text().split()) if out.exists() else set()
        out.write_text("\n".join(sorted(old | set(used))) + "\n")


def move_superseded(raw_dir: Optional[Path] = None) -> list[str]:
    """Move raw records no stage used into raw/_superseded/ (they stay counted in spend accounting)."""
    raw_dir = raw_dir or RAW_DIR
    used = set()
    for f in (raw_dir / "used").glob("*.txt"):
        used |= set(f.read_text().split())
    moved = []
    for p in sorted(raw_dir.rglob("*.json")):
        rel = p.relative_to(raw_dir)
        if rel.parts[0] in ("_superseded", "used") or str(rel) in used or p.name.endswith(".failed.json"):
            continue
        dest = raw_dir / "_superseded" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        p.rename(dest)
        moved.append(str(rel))
    return moved


@dataclass
class CallResult:
    parsed: dict[str, Any]
    record: dict[str, Any]
    path: Path
    cached: bool = False


def call_judge(spec: JudgeSpec, stage: str, item_key: str, prompt_name: str, prompt: str, *,
               data_segments: list[str], forbidden_texts: list[str] = (), raw_dir: Optional[Path] = None,
               validator: Optional[Callable[[dict[str, Any]], list[str]]] = None, max_attempts: int = 2,
               salt: str = "") -> CallResult:
    """Run (or reuse) one judgement. ``salt`` is added to the cache key only, never to the prompt: a replicate
    with a new salt re-asks the identical question, which is what a test-retest needs."""
    raw_dir = raw_dir or RAW_DIR
    schema_name = prompt_name if prompt_name in SCHEMAS else stage
    schema = SCHEMAS[schema_name]
    check_leakage(prompt, data_segments, forbidden_texts)
    system, system_hash = load_prompt("system")
    _, template_hash = load_prompt(prompt_name)
    key_parts: list[Any] = [spec.backend, spec.model, spec.settings, prompt_name, template_hash, system_hash, schema, prompt]
    if salt:  # an empty salt keeps every existing cache key unchanged
        key_parts.append({"salt": salt})
    key_src = json.dumps(key_parts, sort_keys=True)
    key = hashlib.sha256(key_src.encode()).hexdigest()
    out_dir = raw_dir / stage / spec.name
    path = out_dir / f"{item_key}__{key[:12]}.json"
    if path.exists():
        rec = json.loads(path.read_text())
        if rec.get("status") == "ok":
            USED_PATHS.add(path)
            return CallResult(rec["parsed"], rec, path, cached=True)
    failed: list[dict[str, Any]] = []
    errors: list[str] = []
    for attempt in range(1, max_attempts + 1):
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        reservation = 0.0
        meta: Optional[dict[str, Any]] = None
        try:
            if spec.backend == "claude":
                with _LOCK:
                    spent = claude_spent(raw_dir) + _RESERVED[0]
                    cap = claude_call_cap(stage)
                    if spent + cap > CLAUDE_BUDGET_USD:
                        raise JudgeError(f"Judge B budget exhausted: ${spent:.2f} spent or reserved of ${CLAUDE_BUDGET_USD}")
                    reservation = cap
                    _RESERVED[0] += reservation
                try:
                    meta = _claude_call(spec, prompt, schema, system, cap)
                finally:
                    with _LOCK:
                        _RESERVED[0] -= reservation
            elif spec.backend == "codex":
                meta = _codex_call(spec, prompt, schema, system)
                if meta["tool_use_detected"]:
                    failed.append({"attempt": attempt, "error": f"tool use {meta['tool_use_detected']}", **meta})
                    errors.append("tool use detected; discarded")
                    continue
            elif spec.backend == "openrouter":
                meta = _openrouter_call(spec, prompt, schema, system, item_key)
            elif spec.backend == "mock":
                parsed = MOCK_RESPONDERS[stage](prompt, schema)
                meta = {"raw_response": json.dumps(parsed), "usage": None, "cost_usd": 0.0, "latency_s": 0.0,
                        "model_reported": "mock", "model_report_source": "mock", "tool_use_detected": [],
                        "cli_version": "mock"}
            else:
                raise JudgeError(f"unknown backend {spec.backend}")
            parsed = json.loads(meta["raw_response"])
            jsonschema.validate(parsed, schema)
            problems = validator(parsed) if validator else []
            if problems:
                failed.append({"attempt": attempt, "error": "; ".join(problems[:10]), **meta})
                errors.append(f"validation: {problems[:3]}")
                continue
            rec = {"status": "ok", "stage": stage, "item_key": item_key, "judge": spec.name, "backend": spec.backend,
                   "model_requested": spec.model, "settings": spec.settings_dict, "prompt_name": prompt_name,
                   "prompt_template_sha256": template_hash, "system_prompt_sha256": system_hash,
                   "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "cache_key": key, "salt": salt,
                   "started_at": started, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "attempt": attempt, "failed_attempts": failed, **meta, "parsed": parsed}
            out_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
            USED_PATHS.add(path)
            return CallResult(parsed, rec, path)
        except (JudgeError, json.JSONDecodeError, jsonschema.ValidationError, subprocess.TimeoutExpired) as e:
            cost = e.args[1] if isinstance(e, JudgeError) and len(e.args) > 1 else (meta or {}).get("cost_usd")
            failed.append({"attempt": attempt, "error": str(e)[:500], "cost_usd": cost, "backend": spec.backend,
                           "raw_response": (meta or {}).get("raw_response", "")[:2000]})
            errors.append(str(e)[:200])
            if isinstance(e, JudgeError) and "budget exhausted" in str(e):
                break
    # keep the failure record (with any cost incurred) so spend accounting stays complete
    out_dir.mkdir(parents=True, exist_ok=True)
    fail_path = out_dir / f"{item_key}__{key[:12]}.failed.json"
    fail_path.write_text(json.dumps({"status": "failed", "stage": stage, "item_key": item_key, "judge": spec.name,
                                     "backend": spec.backend, "model_requested": spec.model, "cache_key": key,
                                     "failed_attempts": failed, "cost_usd": 0.0}, indent=1, default=str))
    raise JudgeError(f"{stage}/{spec.name}/{item_key} failed after {max_attempts} attempts: {errors}")
