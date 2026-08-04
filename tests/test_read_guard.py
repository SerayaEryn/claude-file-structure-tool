import json
import os
import re
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(__file__), "..", "hooks", "read-guard.py")


def _run_hook(payload):
    result = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _payload(file_path, agent_type="Explore", tool_input_extra=None):
    tool_input = {"file_path": file_path}
    if tool_input_extra:
        tool_input.update(tool_input_extra)
    return {"agent_type": agent_type, "tool_input": tool_input}


def _big_python_file(tmp_path):
    path = tmp_path / "big.py"
    lines = ["def f():", "    pass", ""] * 30
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def test_supported_ext_over_threshold_denies_with_digest(tmp_path):
    path = _big_python_file(tmp_path)
    out = _run_hook(_payload(path))
    data = json.loads(out)
    assert data["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = data["hookSpecificOutput"]["permissionDecisionReason"]
    assert re.search(r"L\d+", reason)
    assert "does not" not in reason  # sanity: not the plain fallback message
    assert "structural" in reason.lower()


def test_unparseable_file_falls_back_to_plain_message(tmp_path):
    path = tmp_path / "broken.py"
    path.write_text("x = 1\n" * 60)  # no declarations -> build_digest returns None
    out = _run_hook(_payload(str(path)))
    data = json.loads(out)
    assert data["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = data["hookSpecificOutput"]["permissionDecisionReason"]
    assert "mcp__plugin_file-structure_file-structure__file_structure" in reason


def test_non_explore_agent_allows(tmp_path):
    path = _big_python_file(tmp_path)
    out = _run_hook(_payload(path, agent_type="claude"))
    assert out == ""


def test_missing_agent_type_allows(tmp_path):
    path = _big_python_file(tmp_path)
    out = _run_hook({"tool_input": {"file_path": path}})
    assert out == ""


def test_offset_allows(tmp_path):
    path = _big_python_file(tmp_path)
    out = _run_hook(_payload(path, tool_input_extra={"offset": 1}))
    assert out == ""


def test_limit_allows(tmp_path):
    path = _big_python_file(tmp_path)
    out = _run_hook(_payload(path, tool_input_extra={"limit": 10}))
    assert out == ""


def test_unsupported_extension_allows(tmp_path):
    path = tmp_path / "big.txt"
    path.write_text("line\n" * 100)
    out = _run_hook(_payload(str(path)))
    assert out == ""


def test_small_file_allows(tmp_path):
    path = tmp_path / "small.py"
    path.write_text("def f():\n    pass\n")
    out = _run_hook(_payload(str(path)))
    assert out == ""
