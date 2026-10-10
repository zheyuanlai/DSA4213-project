"""Secret scanner catches planted secrets (fake values built at runtime) and never echoes them."""
import subprocess

from src.security_scan import GENERIC_PATTERNS, live_secret_patterns, run_scan, scan_text

FAKE_BODY = "".join("0123456789abcdef"[(i * 7) % 16] for i in range(64))  # synthetic, not a real key
FAKE_KEY = "sk-or-v1-" + FAKE_BODY


def test_generic_patterns_detect_fake_key():
    f = scan_text(f"x = '{FAKE_KEY}'", "a.py", GENERIC_PATTERNS)
    assert [x.pattern for x in f] == ["openrouter_key"]
    assert FAKE_KEY not in str(f[0])


def test_live_key_fragments(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    pats = live_secret_patterns()
    f = scan_text(f"partial {FAKE_BODY[-16:]} leaked", "b.txt", pats)
    assert any(x.pattern == "live_key_fragment_tail" for x in f)


def test_tree_and_history_scan(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    run = lambda *a: subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)  # noqa: E731
    run("init", "-q")
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    (tmp_path / "ok.txt").write_text("nothing here\n")
    (tmp_path / "leak.txt").write_text(f"KEY={FAKE_KEY}\n")
    run("add", ".")
    run("commit", "-qm", "c1")
    (tmp_path / "leak.txt").unlink()
    run("add", "-A")
    run("commit", "-qm", "remove leak")
    findings = run_scan(tmp_path, include_history=True)
    assert any("leak.txt" in f.where and f.pattern == "live_key_full" for f in findings), findings
    # deleting in the newest commit is not enough: history still flagged
    assert all("ok.txt" not in f.where for f in findings)
    (tmp_path / ".env").write_text("X=1\n")
    findings = run_scan(tmp_path, include_history=False)
    assert any(f.pattern == "forbidden_file_would_be_committed" for f in findings)
