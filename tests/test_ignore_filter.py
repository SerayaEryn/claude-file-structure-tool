from ignore_filter import IgnoreMatcher, _is_ignored


def test_matches_gitignore_pattern(tmp_path):
    (tmp_path / ".gitignore").write_text("*.log\n")
    matcher = IgnoreMatcher(tmp_path)
    assert matcher.is_ignored("debug.log") is True


def test_non_matching_path_is_not_ignored(tmp_path):
    (tmp_path / ".gitignore").write_text("*.log\n")
    matcher = IgnoreMatcher(tmp_path)
    assert matcher.is_ignored("keep.txt") is False


def test_aiignore_can_reinclude_after_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text("*.log\n")
    (tmp_path / ".aiignore").write_text("!important.log\n")
    matcher = IgnoreMatcher(tmp_path)
    assert matcher.is_ignored("important.log") is False
    assert matcher.is_ignored("other.log") is True


def test_directory_level_ignore_applies_to_nested_file(tmp_path):
    (tmp_path / ".gitignore").write_text("build/\n")
    (tmp_path / "build").mkdir()
    matcher = IgnoreMatcher(tmp_path)
    assert matcher.is_ignored("build/output.txt") is True


def test_malformed_ignore_file_fails_soft(tmp_path, monkeypatch):
    (tmp_path / ".gitignore").write_text("*.log\n")

    def _raise(_lines):
        raise ValueError("bad pattern")

    monkeypatch.setattr("ignore_filter.GitIgnoreSpec.from_lines", _raise)
    matcher = IgnoreMatcher(tmp_path)
    assert matcher.is_ignored("debug.log") is False


def test_root_and_empty_relpath_are_never_ignored(tmp_path):
    (tmp_path / ".gitignore").write_text("*\n")
    matcher = IgnoreMatcher(tmp_path)
    assert matcher.is_ignored("") is False
    assert matcher.is_ignored(".") is False


def test_is_ignored_refuses_path_matched_by_repo_gitignore(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("secret.txt\n")
    (tmp_path / "secret.txt").write_text("hush")
    assert _is_ignored(str(tmp_path / "secret.txt")) is True


def test_is_ignored_allows_path_not_matched_by_repo_gitignore(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("secret.txt\n")
    (tmp_path / "readme.txt").write_text("hi")
    assert _is_ignored(str(tmp_path / "readme.txt")) is False


def test_is_ignored_without_git_repo_falls_back_to_file_dir(tmp_path):
    plain = tmp_path / "plain.txt"
    plain.write_text("hi")
    assert _is_ignored(str(plain)) is False
