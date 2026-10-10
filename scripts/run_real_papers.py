"""Secondary real-paper study: 12 packages x C1-C4 (frozen config). Re-running resumes idempotently."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_experiment import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["--config", "configs/frozen_primary.yaml", "--cases", "data/real_papers/packages", "--family", "real_papers",
                   "--run-tag", "real_v1", "--stage", "real", "--conditions", "C1,C2,C3,C4", "--workers", "2"] + sys.argv[1:]))
