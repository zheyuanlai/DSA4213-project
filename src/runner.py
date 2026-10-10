"""Resumable experiment runner (job manifest: pending/running/completed/failed).

* Each (case, condition) job writes outputs/<family>/<model_slug>/<condition>/<case_id>.json.
* outputs/<family>/<model_slug>/job_manifest.json holds the latest status per job; every state
  transition is also appended to outputs/run_manifest.jsonl (append-only event log).
* Completed and failed jobs are NOT re-run on resume (failures stay in the denominator);
  jobs left 'running' by an interrupted process have no output and are re-run.
* Fatal API errors (401/402/403/400) and budget exhaustion stop the run immediately.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

import yaml

from src.agent import FATAL, atomic_write_json, run_case, sha256_obj
from src.conditions import CONDITIONS
from src.cost_guard import CostGuard, Pricing, now_iso
from src.openrouter_client import BaseClient, OpenRouterClient
from src.package_schema import CaseRecord
from src.prompts import prompt_hashes
from src.schemas import RunRecord

ROOT = Path(__file__).resolve().parent.parent


def code_hash() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "src").glob("*.py")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def git_commit() -> Optional[str]:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return None


def git_dirty() -> Optional[bool]:
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--", "src", "prompts", "configs"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        return bool(out.strip())
    except Exception:
        return None


def load_config(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text())


def model_slug(model_id: str) -> str:
    return model_id.replace("/", "__").replace(":", "_")


def load_cases(path: str | Path) -> list[CaseRecord]:
    p = Path(path)
    recs: list[CaseRecord] = []
    if p.is_dir():
        for f in sorted(p.glob("*.json")):
            recs.append(CaseRecord.model_validate_json(f.read_text()))
    else:
        for line in p.read_text().splitlines():
            if line.strip():
                recs.append(CaseRecord.model_validate_json(line))
    return recs


def make_guard(cfg: dict[str, Any]) -> CostGuard:
    pr = cfg["model"].get("pricing")
    pricing = Pricing(pr["prompt_per_mtok"] / 1e6, pr["completion_per_mtok"] / 1e6) if pr else Pricing.conservative()
    b = cfg["budget"]
    return CostGuard(ledger_path=ROOT / cfg["paths"]["ledger"], hard_cap_usd=float(b["hard_cap_usd"]),
                     stage_caps={k: float(v) for k, v in b["stage_caps"].items()}, pricing=pricing,
                     max_inflight=int(b.get("max_inflight", 1)))


def make_client(cfg: dict[str, Any], guard: CostGuard) -> OpenRouterClient:
    m = cfg["model"]
    return OpenRouterClient(model_id=m["id"], provider_routing=m.get("provider_routing") or {},
                            decoding=m.get("decoding") or {}, cost_guard=guard,
                            timeout_s=float(m.get("timeout_s", 120)), max_retries=int(m.get("max_retries", 3)),
                            code_hash=code_hash())


class JobManifest:
    def __init__(self, path: Path, events_path: Path, run_tag: str):
        self.path, self.events_path, self.run_tag = path, events_path, run_tag
        self._lock = threading.Lock()
        self.jobs: dict[str, dict[str, Any]] = {}
        if path.exists():
            self.jobs = json.loads(path.read_text()).get("jobs", {})

    @staticmethod
    def key(case_id: str, cond: str) -> str:
        return f"{case_id}|{cond}"

    def status(self, case_id: str, cond: str) -> str:
        return self.jobs.get(self.key(case_id, cond), {}).get("status", "pending")

    def set(self, case_id: str, cond: str, status: str, **extra: Any) -> None:
        with self._lock:
            k = self.key(case_id, cond)
            prev = self.jobs.get(k, {})
            entry = {"status": status, "updated": now_iso(), "run_tag": self.run_tag,
                     "restarts": prev.get("restarts", 0) + (1 if prev.get("status") == "running" and status == "running" else 0)}
            entry.update(extra)
            self.jobs[k] = entry
            atomic_write_json(self.path, {"run_tag": self.run_tag, "jobs": self.jobs})
            self.events_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.events_path, "a") as f:
                f.write(json.dumps({"ts": entry["updated"], "run_tag": self.run_tag, "job": k, "status": status,
                                    **{kk: vv for kk, vv in extra.items() if kk in ("failure", "cost_usd")}}) + "\n")


def run_experiment(cfg: dict[str, Any], cases: list[CaseRecord], conditions: list[str], *, family: str,
                   run_tag: str, stage: str, client: Optional[BaseClient] = None, out_base: Optional[Path] = None,
                   workers: int = 1, events_path: Optional[Path] = None) -> dict[str, Any]:
    for c in conditions:
        if c not in CONDITIONS:
            raise ValueError(f"unknown condition {c}")
    guard = None
    if client is None:
        guard = make_guard(cfg)
        client = make_client(cfg, guard)
    out_base = out_base or ROOT / "outputs"
    out_root = out_base / family / model_slug(client.model_id)
    manifest = JobManifest(out_root / "job_manifest.json", events_path or out_base / "run_manifest.jsonl", run_tag)
    run_meta = {
        "run_tag": run_tag, "stage": stage, "prompt_hashes": prompt_hashes(), "code_hash": code_hash(),
        "config_hash": sha256_obj(cfg)[:16], "git_commit": git_commit(), "git_dirty": git_dirty(),
    }
    atomic_write_json(out_root / f"run_meta_{run_tag}.json", {**run_meta, "config": cfg, "conditions": conditions,
                                                              "case_ids": [c.case_id for c in cases],
                                                              "is_mock": client.is_mock, "started_at": now_iso()})
    vcfg = cfg.get("verifier", {})

    def skip(cond: str, case_id: str) -> bool:
        st = manifest.status(case_id, cond)
        out_exists = (out_root / cond / f"{case_id}.json").exists()
        return st in ("completed", "failed") and out_exists

    def on_done(rr: RunRecord) -> None:
        manifest.set(rr.case_id, rr.condition, rr.status, failure=rr.failure, cost_usd=rr.totals.get("cost_usd"))

    stop_reason: Optional[str] = None

    def do_case(rec: CaseRecord) -> None:
        todo = [c for c in conditions if not skip(c, rec.case_id)]
        for c in todo:
            manifest.set(rec.case_id, c, "running")
        run_case(client, rec, todo, out_root, run_meta, on_done=on_done,
                 max_tool_calls=int(vcfg.get("max_tool_calls", 4)), max_claims=int(vcfg.get("max_claims", 6)))

    if workers <= 1:
        for rec in cases:
            try:
                do_case(rec)
            except FATAL as e:
                stop_reason = f"{type(e).__name__}: {e}"
                break
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(do_case, rec): rec for rec in cases}
            for fut in as_completed(futs):
                try:
                    fut.result()
                except FATAL as e:
                    stop_reason = f"{type(e).__name__}: {e}"
                    for f in futs:
                        f.cancel()
    # jobs still 'running' after a fatal stop are reset to pending (no output exists)
    for k, v in list(manifest.jobs.items()):
        if v.get("status") == "running":
            case_id, cond = k.split("|")
            if not (out_root / cond / f"{case_id}.json").exists():
                manifest.set(case_id, cond, "pending", failure=f"interrupted: {stop_reason}")
    statuses: dict[str, int] = {}
    for c in cases:
        for cond in conditions:
            st = manifest.status(c.case_id, cond)
            statuses[st] = statuses.get(st, 0) + 1
    summary = {"run_tag": run_tag, "out_root": str(out_root), "statuses": statuses, "stop_reason": stop_reason,
               "planned": len(cases) * len(conditions)}
    if guard is not None:
        summary["ledger"] = guard.summary()
    return summary
