"""Smoke tests for experiment project module."""

from src.experiments.project import BASE_PROJECT_FILES, CLEAN_DIRS, clean_project


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
