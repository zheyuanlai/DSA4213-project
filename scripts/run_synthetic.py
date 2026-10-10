"""Primary held-out run: 32 TEST cases x 7 conditions (frozen config). Re-running resumes idempotently."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_experiment import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["--config", "configs/frozen_primary.yaml", "--cases", "data/synthetic/test.jsonl", "--family", "synthetic",
                   "--run-tag", "primary_v1", "--stage", "main", "--workers", "2"] + sys.argv[1:]))
