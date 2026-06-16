"""Smoke tests for experiment project module."""

from src.experiments.project import (
    BASE_PROJECT_FILES,
    CLEAN_DIRS,
    _runtime_exception_result,
    clean_project,
    ensure_base_project,
)


class TestProjectConstants:
    """Verify project module constants."""

    def test_clean_dirs(self):
        assert "src" in CLEAN_DIRS
        assert "dist" in CLEAN_DIRS

    def test_base_project_files(self):
        assert "package.json" in BASE_PROJECT_FILES
        assert "tsconfig.json" in BASE_PROJECT_FILES


class TestCleanProject:
    """Verify clean_project removes expected directories."""

    def test_clean_project_removes_src(self, temp_dir):
        src_dir = temp_dir / "src"
        src_dir.mkdir()
        (src_dir / "test.ts").write_text("content")

        clean_project(temp_dir)
        assert not src_dir.exists()

    def test_clean_project_skips_nonexistent_dirs(self, temp_dir):
        clean_project(temp_dir)


class TestRuntimeExceptionResult:
    """Verify _runtime_exception_result builds correct payload."""

    def test_returns_expected_structure(self):
        exc = RuntimeError("NPM install failed")
        result = _runtime_exception_result(exc)
        assert result["valid"] is False
        assert result["install_success"] is False
        assert result["build_success"] is False
        assert result["start_success"] is False
        assert result["errors"]["runtime"]["message"] == "NPM install failed"


class TestCleanProjectExtended:
    """Verify clean_project handles all CLEAN_DIRS."""

    def test_clean_project_removes_dist(self, temp_dir):
        dist_dir = temp_dir / "dist"
        dist_dir.mkdir()
        (dist_dir / "bundle.js").write_text("content")
        clean_project(temp_dir)
        assert not dist_dir.exists()

    def test_clean_project_removes_data(self, temp_dir):
        data_dir = temp_dir / "data"
        data_dir.mkdir()
        (data_dir / "db.sqlite").write_text("data")
        clean_project(temp_dir)
        assert not data_dir.exists()

    def test_clean_project_removes_multiple_dirs(self, temp_dir):
        for name in ["src", "dist", "data"]:
            d = temp_dir / name
            d.mkdir()
            (d / "file.txt").write_text("content")
        clean_project(temp_dir)
        for name in ["src", "dist", "data"]:
            assert not (temp_dir / name).exists()


class TestEnsureBaseProject:
    """Verify ensure_base_project file copying."""

    def test_when_base_dir_missing_does_nothing(self, temp_dir, monkeypatch):
        monkeypatch.setattr("src.experiments.project.BASE_NEST_PROJECT_DIR", temp_dir / "nonexistent")
        ensure_base_project(temp_dir)

    def test_when_base_dir_exists_copies_base_files(self, temp_dir, monkeypatch):
        base_dir = temp_dir / "base_nest"
        base_dir.mkdir()
        (base_dir / "package.json").write_text('{"name": "test"}')
        (base_dir / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (base_dir / "random.txt").write_text("should not copy")

        monkeypatch.setattr("src.experiments.project.BASE_NEST_PROJECT_DIR", base_dir)

        dest_dir = temp_dir / "project"
        dest_dir.mkdir()
        (dest_dir / "random.txt").write_text("original")

        ensure_base_project(dest_dir)
        assert (dest_dir / "package.json").exists()
        assert (dest_dir / "tsconfig.json").exists()
        assert (dest_dir / "random.txt").read_text() == "original"


class TestConstantsExtended:
    """Verify additional constant values."""

    def test_clean_dirs_contains_data(self):
        assert "data" in CLEAN_DIRS

    def test_clean_dirs_complete(self):
        assert CLEAN_DIRS == ["src", "dist", "data"]

    def test_base_project_files_complete(self):
        assert BASE_PROJECT_FILES == {
            "package.json",
            "tsconfig.json",
            "tsconfig.build.json",
            "nest-cli.json",
            "eslint.config.mjs",
        }
