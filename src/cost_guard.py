"""Hard-capped OpenRouter spend control with one append-only, secret-free ledger.

* Before every call: reserve an upper-bound estimate; refuse if
  spent + in-flight reservations + estimate would exceed the hard cap or stage cap.
* After every call: append the actual provider-reported cost (usage.cost) when present,
  otherwise a token-based estimate (labelled), otherwise the reserved upper bound (labelled).
* Thread-safe (lock + bounded semaphore for <= max_inflight requests) and process-safe
  (fcntl lock on the ledger; spend is re-read from the ledger at reservation time).
* The ledger never contains request headers, prompts, environment variables or keys.
"""
from __future__ import annotations

import fcntl
import json
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Pricing:
    prompt_per_token: float
    completion_per_token: float

    @classmethod
    def conservative(cls) -> "Pricing":
        return cls(prompt_per_token=1.0e-6, completion_per_token=3.0e-6)


@dataclass
class CostGuard:
    ledger_path: Path
    hard_cap_usd: float
    stage_caps: dict[str, float]
    pricing: Pricing
    max_inflight: int = 2
    safety_factor: float = 1.5
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _reserved: float = field(default=0.0, init=False)
    _reserved_by_stage: dict[str, float] = field(default_factory=dict, init=False)
    _sem: threading.BoundedSemaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.ledger_path = Path(self.ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.touch(exist_ok=True)
        self._sem = threading.BoundedSemaphore(self.max_inflight)

    # ------------------------------------------------------------------ ledger
    def _read_ledger(self) -> list[dict[str, Any]]:
        with open(self.ledger_path, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                lines = f.read().splitlines()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        out = []
        for ln in lines:
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
        return out

    def spent(self, stage: str | None = None) -> float:
        tot = 0.0
        for e in self._read_ledger():
            if stage is None or e.get("stage") == stage:
                tot += float(e.get("cost_usd") or 0.0)
        return tot

    def summary(self) -> dict[str, Any]:
        rows = self._read_ledger()
        by_stage: dict[str, float] = {}
        by_source: dict[str, float] = {}
        for e in rows:
            by_stage[e.get("stage", "?")] = by_stage.get(e.get("stage", "?"), 0.0) + float(e.get("cost_usd") or 0)
            by_source[e.get("cost_source", "?")] = by_source.get(e.get("cost_source", "?"), 0.0) + float(e.get("cost_usd") or 0)
        return {
            "n_entries": len(rows),
            "total_usd": round(sum(by_stage.values()), 6),
            "by_stage": {k: round(v, 6) for k, v in by_stage.items()},
            "by_cost_source": {k: round(v, 6) for k, v in by_source.items()},
            "hard_cap_usd": self.hard_cap_usd,
            "stage_caps": self.stage_caps,
        }

    def append(self, entry: dict[str, Any]) -> None:
        forbidden = {"authorization", "headers", "api_key", "env", "messages", "prompt"}
        bad = forbidden & {k.lower() for k in entry}
        if bad:
            raise ValueError(f"refusing to log sensitive fields {bad}")
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True, default=str)
        with open(self.ledger_path, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    # --------------------------------------------------------------- estimates
    def estimate_upper_bound(self, prompt_chars: int, max_tokens: int) -> float:
        # ~3 chars/token is conservative for English+JSON; completion bounded by max_tokens
        # (reasoning tokens are counted inside max_tokens by OpenRouter when reasoning is on).
        pt = prompt_chars / 3.0
        return self.safety_factor * (pt * self.pricing.prompt_per_token + max_tokens * self.pricing.completion_per_token)

    def estimate_from_tokens(self, prompt_tokens: int, completion_tokens: int) -> float:
        return prompt_tokens * self.pricing.prompt_per_token + completion_tokens * self.pricing.completion_per_token

    # ------------------------------------------------------------- reservation
    @contextmanager
    def reserve(self, estimate: float, stage: str) -> Iterator[None]:
        if stage not in self.stage_caps:
            raise BudgetExceeded(f"unknown stage {stage!r}; configure a stage cap first")
        self._sem.acquire()
        try:
            with self._lock:
                spent_total = self.spent()
                spent_stage = self.spent(stage)
                if spent_total + self._reserved + estimate > self.hard_cap_usd:
                    raise BudgetExceeded(
                        f"hard cap ${self.hard_cap_usd:.2f}: spent ${spent_total:.4f} + reserved ${self._reserved:.4f} "
                        f"+ next ${estimate:.4f} would exceed"
                    )
                stage_res = self._reserved_by_stage.get(stage, 0.0)
                if spent_stage + stage_res + estimate > self.stage_caps[stage]:
                    raise BudgetExceeded(
                        f"stage {stage!r} cap ${self.stage_caps[stage]:.2f}: spent ${spent_stage:.4f} + reserved "
                        f"${stage_res:.4f} + next ${estimate:.4f} would exceed"
                    )
                self._reserved += estimate
                self._reserved_by_stage[stage] = stage_res + estimate
            try:
                yield
            finally:
                with self._lock:
                    self._reserved -= estimate
                    self._reserved_by_stage[stage] -= estimate
        finally:
            self._sem.release()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"
