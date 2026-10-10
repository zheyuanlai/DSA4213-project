"""DEV-split run (all 7 conditions). Thin wrapper around scripts/run_experiment.py; extra args pass through."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_experiment import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["--config", "configs/frozen_primary.yaml", "--cases", "data/synthetic/dev.jsonl", "--family", "dev",
                   "--run-tag", "dev_rerun", "--stage", "dev"] + sys.argv[1:]))
