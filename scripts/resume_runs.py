"""Resume an interrupted run: identical to re-running the original command (the job manifest skips
completed/failed jobs and re-runs only jobs left pending/running without output).

  python scripts/resume_runs.py synthetic      # resumes the primary TEST run
  python scripts/resume_runs.py real           # resumes the real-paper run
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = {"synthetic": "run_synthetic.py", "real": "run_real_papers.py", "dev": "run_dev.py"}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "synthetic"
    sys.exit(subprocess.call([sys.executable, str(HERE / TARGET[which])] + sys.argv[2:]))
