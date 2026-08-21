"""流水线步骤共享工具。"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE = ROOT / "workspace"
PROMPTS = ROOT / "prompts"


def ws_dir(account: str) -> Path:
    d = WORKSPACE / account
    d.mkdir(parents=True, exist_ok=True)
    return d


def step_dir(account: str, step: str) -> Path:
    d = ws_dir(account) / step
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def external_exists(p: str) -> bool:
    return bool(p) and (Path(p).exists() or shutil.which(p) is not None)


def run_cmd(cmd, cwd=None, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:  # noqa
        return -1, "", str(e)


def prompt_path(name: str) -> Path:
    return PROMPTS / name
