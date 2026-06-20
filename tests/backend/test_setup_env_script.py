"""Tests for the local environment bootstrap script."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "setup-env.sh"


def _write_fake_op(bin_dir: Path) -> None:
    op = bin_dir / "op"
    op.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" != "inject" ]]; then
  exit 1
fi
in_file=""
out_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --in-file|-i)
      in_file="$2"
      shift 2
      ;;
    --out-file|-o)
      out_file="$2"
      shift 2
      ;;
    --file-mode|--force)
      shift
      if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
        shift
      fi
      ;;
    *)
      shift
      ;;
  esac
done
cp "$in_file" "$out_file"
chmod 600 "$out_file"
""",
        encoding="utf-8",
    )
    op.chmod(0o755)


def test_setup_env_generates_env_with_op_inject(tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_op(bin_dir)
    template = tmp_path / "template.env"
    output = tmp_path / ".env"
    template.write_text(
        "\n".join(
            [
                "EUMPA_DATA_ROOT=runtime-data",
                "EUMPA_DATABASE_URL=sqlite:///runtime-data/eumpa.db",
                "EUMPA_COMFYUI_URL=http://localhost:8188",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--template",
            str(template),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Wrote" in result.stdout
    assert output.read_text(encoding="utf-8") == template.read_text(encoding="utf-8")
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert (ROOT / "runtime-data").is_dir()
    (ROOT / "runtime-data").rmdir()


def test_setup_env_refuses_to_overwrite_without_force(tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_op(bin_dir)
    template = tmp_path / "template.env"
    output = tmp_path / ".env"
    template.write_text("EUMPA_DATA_ROOT=data\n", encoding="utf-8")
    output.write_text("existing=true\n", encoding="utf-8")

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--template",
            str(template),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "already exists" in result.stderr
    assert output.read_text(encoding="utf-8") == "existing=true\n"


def test_setup_env_reports_missing_op(tmp_path: Path):
    template = tmp_path / "template.env"
    output = tmp_path / ".env"
    template.write_text("EUMPA_DATA_ROOT=data\n", encoding="utf-8")

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--template",
            str(template),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env={**os.environ, "PATH": "/usr/bin:/bin"},
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "1Password CLI" in result.stderr
    assert not output.exists()
