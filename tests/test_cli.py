import subprocess, sys, os
from pathlib import Path


def _env_for_repo(repo_root):
    env = os.environ.copy()
    src = str(repo_root / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def test_cli_smoke():
    root = Path(__file__).resolve().parents[1]
    data = root / 'examples' / 'messy_clinical_data.csv'
    out = subprocess.run([sys.executable, '-m', 'datasanity.cli', 'check', str(data)], cwd=root, text=True, capture_output=True, check=True, env=_env_for_repo(root))
    assert 'DataSanity report' in out.stdout
