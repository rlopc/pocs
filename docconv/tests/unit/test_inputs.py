"""The real input documents must never change."""

from __future__ import annotations

import hashlib

from tests.conftest import REAL_INPUTS


def test_real_inputs_match_sha256sums() -> None:
    lines = (REAL_INPUTS / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    expected: dict[str, str] = {}
    for line in lines:
        digest, name = line.split(maxsplit=1)
        expected[name] = digest
    assert len(expected) == 9
    on_disk = {p.name for p in REAL_INPUTS.iterdir() if p.name.startswith("b2-week_")}
    assert on_disk == set(expected)
    for name, digest in expected.items():
        assert hashlib.sha256((REAL_INPUTS / name).read_bytes()).hexdigest() == digest, name
