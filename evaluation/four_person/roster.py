"""Who annotates what, file names, stage names, the fixed seed and default paths.

Every other module takes paths explicitly; `Paths.default()` is only used by the CLI.
"""
from __future__ import annotations

import csv
import hashlib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Fixed, documented seed for (1) tie-breaking between equally balanced team allocations and
# (2) every per-person row-order shuffle. Changing it would change the assignment, so `assign`
# refuses to overwrite an existing assignment file.
SEED = 4213
ASSIGNMENT_VERSION = "four_person_v1"


@dataclass(frozen=True)
class Annotator:
    id: str
    name: str
    team: str
    partner: str
    # True when this person can open the coordinator-private files (gold, condition mapping, raw
    # outputs). A declaration of "no exposure" then still cannot be verified, so their labels are
    # reported as at best self-reported blind.
    coordinator_access: bool = False

    @property
    def tag(self) -> str:
        return f"{self.id}_{self.name}"


ANNOTATORS: dict[str, Annotator] = {
    "A": Annotator("A", "Zheyuan", "AB", "B", coordinator_access=True),
    "B": Annotator("B", "Yuxin", "AB", "A"),
    "C": Annotator("C", "Jiajun", "CD", "D"),
    "D": Annotator("D", "Xinkai", "CD", "C"),
}
TEAMS: dict[str, tuple[str, str]] = {"AB": ("A", "B"), "CD": ("C", "D")}

# Coordinator-private rows that were displayed on screen in the AI-assistant session that built this workflow
# (2026-10-15), disclosed so that Annotator A (the coordinator) can declare them precisely. Only the refs that
# fall inside A's own assignment are named in A's README; the rest are only counted.
SESSION_EXPOSURE = {"date": "2026-10-15", "alias_rows_case_refs": ["K01", "K02", "K03", "K04"],
                    "condition_rows_synthetic": {"K05": 2}, "condition_rows_real": {"RP-01": 2},
                    "n_pass2_checklist_id_names": 3}

# Distribution stages (one zip per person per stage) and the files a person hands back.
STAGES = ("training", "pass1", "pass2", "real")
STAGE_DIRS = {"training": "0_training", "pass1": "1_pass1", "pass2": "2_pass2", "real": "3_real"}
SUBMISSION_KINDS = ("declaration", "pass1", "pass2", "real_outputs", "real_sentences", "timelog")
ADJUDICATION_KINDS = ("synthetic", "real")


def sheet_name(who: str, kind: str) -> str:
    """File name of a person's sheet; identical for the blank template and the returned file."""
    a = ANNOTATORS[who]
    return {"pass1": f"{a.tag}_pass1.csv", "pass2": f"{a.tag}_pass2.csv",
            "real_outputs": f"{a.tag}_real_outputs.csv", "real_sentences": f"{a.tag}_real_sentences.csv",
            "declaration": f"{a.tag}_blinding_declaration.csv", "timelog": f"{a.tag}_time_log.csv"}[kind]


def viewer_name(who: str, stage: str) -> str:
    return f"{ANNOTATORS[who].tag}_{stage}_viewer.html"


def zip_name(who: str, stage: str) -> str:
    return f"{ANNOTATORS[who].tag}__{STAGE_DIRS[stage]}.zip"


def readme_name(who: str) -> str:
    return f"README_{ANNOTATORS[who].tag}.md"


@dataclass
class Paths:
    """All locations used by the workflow. Original inputs are only ever read."""
    root: Path
    # original, frozen inputs (read-only)
    syn_packet: Path
    pass1_packages: Path
    pass2_packages: Path
    real_packet: Path
    real_sent_packet: Path
    real_packages: Path
    test_cases: Path
    test_rubric: Path
    dev_cases: Path
    dev_rubric: Path
    guide: Path
    demo: Path
    # coordinator-private inputs (read-only)
    alias_map: Path
    condition_mapping: Path
    condition_mapping_real: Path
    gold: Path
    # new outputs
    fp_dir: Path          # annotation/four_person (annotator-safe docs, assignment, logs)
    packets_dir: Path     # annotation/four_person/packets (gitignored)
    dist_dir: Path        # annotation/four_person/dist (gitignored zips)
    logs_dir: Path        # annotation/four_person/logs
    private_dir: Path     # private/four_person (gitignored; coordinator-only)

    @classmethod
    def default(cls, root: Optional[Path] = None) -> "Paths":
        r = root or Path(__file__).resolve().parents[2]
        ann, fp, priv = r / "annotation", r / "annotation" / "four_person", r / "private"
        return cls(root=r, syn_packet=ann / "blinded_synthetic.csv", pass1_packages=ann / "pass1" / "packages",
                   pass2_packages=ann / "pass2" / "packages", real_packet=ann / "real" / "blinded_real_papers.csv",
                   real_sent_packet=ann / "real" / "blinded_real_papers_sentences.csv",
                   real_packages=ann / "real" / "packages", test_cases=r / "data" / "synthetic" / "test.jsonl",
                   test_rubric=r / "data" / "synthetic" / "rubrics" / "test_rubric.jsonl",
                   dev_cases=r / "data" / "synthetic" / "dev.jsonl",
                   dev_rubric=r / "data" / "synthetic" / "rubrics" / "dev_rubric.jsonl",
                   guide=ann / "ANNOTATION_GUIDE.md", demo=ann / "demo_example_NOT_TEST.md",
                   alias_map=priv / "case_alias_map.csv", condition_mapping=priv / "condition_mapping.csv",
                   condition_mapping_real=priv / "condition_mapping_real.csv", gold=priv / "gold" / "test_gold.jsonl",
                   fp_dir=fp, packets_dir=fp / "packets", dist_dir=fp / "dist", logs_dir=fp / "logs",
                   private_dir=priv / "four_person")

    # derived locations
    @property
    def assignment_json(self) -> Path:
        return self.fp_dir / "assignment.json"

    @property
    def assignment_private(self) -> Path:
        return self.private_dir / "assignment_private.csv"

    @property
    def private_hashes(self) -> Path:
        return self.private_dir / "private_file_hashes.json"

    @property
    def submissions_dir(self) -> Path:
        return self.private_dir / "submissions"

    def team_dir(self, team: str) -> Path:
        return self.private_dir / "teams" / team

    @property
    def final_dir(self) -> Path:
        return self.private_dir / "final"

    def person_dir(self, who: str) -> Path:
        return self.packets_dir / ANNOTATORS[who].tag

    def stage_dir(self, who: str, stage: str) -> Path:
        return self.person_dir(who) / STAGE_DIRS[stage]

    def protected_private_files(self) -> list[Path]:
        """Original coordinator-private files that this workflow must never modify."""
        p = self.alias_map.parent
        return [self.alias_map, self.condition_mapping, self.condition_mapping_real, self.gold,
                p / "packet_meta_synthetic.json", p / "packet_meta_real.json"]

    def original_packet_files(self) -> list[Path]:
        files = [self.syn_packet, self.real_packet, self.real_sent_packet, self.guide, self.demo]
        for d in (self.pass1_packages, self.pass2_packages, self.real_packages):
            files += sorted(d.glob("*.md"))
        return files


# ----------------------------------------------------------------------------- small helpers
def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(s: Optional[str]) -> str:
    """Whitespace- and Unicode-normalised text, for 'text unchanged' comparisons."""
    return " ".join(unicodedata.normalize("NFC", s or "").split())


def read_csv_any(path: Path) -> list[dict[str, str]]:
    """Read a CSV that may carry a UTF-8 BOM (Excel 'CSV UTF-8' adds one)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{(k or "").strip(): (v if v is not None else "") for k, v in r.items()} for r in csv.DictReader(f)]


def csv_header(path: Path) -> list[str]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [h.strip() for h in next(csv.reader(f), [])]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str], bom: bool = False) -> None:
    """bom=True for sheets students open in Excel (it then shows UTF-8 symbols such as ± and ≥ correctly).
    Coordinator/consensus files are written without a BOM, exactly like the original scripts expect."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig" if bom else "utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
