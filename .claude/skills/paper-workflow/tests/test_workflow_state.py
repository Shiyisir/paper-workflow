"""Test workflow_state.py core read/write/validate."""

import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import workflow_state as ws


class TestFindProjectRoot:
    def test_finds_project_with_state(self, tmp_paper_project):
        """Should find project root when .paper-workflow/state.yaml exists."""
        pw_dir = tmp_paper_project / ".paper-workflow"
        pw_dir.mkdir(parents=True, exist_ok=True)
        (pw_dir / "state.yaml").write_text("schema_version: 1\n", encoding="utf-8")

        found = ws.find_project_root(tmp_paper_project)
        assert found == tmp_paper_project.resolve()

    def test_finds_project_with_config(self, tmp_paper_project):
        """Should find project root with only config.yaml."""
        pw_dir = tmp_paper_project / ".paper-workflow"
        pw_dir.mkdir(parents=True, exist_ok=True)
        (pw_dir / "config.yaml").write_text("project_id: test\n", encoding="utf-8")

        found = ws.find_project_root(tmp_paper_project)
        assert found == tmp_paper_project.resolve()

    def test_returns_none_if_no_project(self, tmp_path):
        """Should return None for non-project directories."""
        found = ws.find_project_root(tmp_path)
        assert found is None


class TestSaveAndLoad:
    def test_save_and_load_roundtrip(self, tmp_paper_project):
        """State saved and loaded back should be identical."""
        pw_dir = tmp_paper_project / ".paper-workflow"
        pw_dir.mkdir(parents=True, exist_ok=True)

        # Write a minimal config so load_state works
        config = {"project_id": "test-001", "paper_type": "course_paper"}
        with open(pw_dir / "config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        state = {
            "schema_version": 1,
            "project_id": "test-001",
            "paper_type": "course_paper",
            "current_stage": "requirements",
            "stages": {
                "requirements": {
                    "status": "in_progress",
                    "depends_on": [],
                    "started_at": "2026-01-01T00:00:00Z",
                    "completed_at": None,
                    "qa_status": "pending",
                    "qa_report": None,
                    "artifacts": [],
                    "blockers": [],
                }
            },
            "overrides": [],
        }

        saved = ws.save_state(state, tmp_paper_project)
        assert saved.exists()

        loaded = ws.load_state(tmp_paper_project)
        assert loaded["state"]["project_id"] == "test-001"
        assert loaded["state"]["stages"]["requirements"]["status"] == "in_progress"

    def test_load_state_missing_files(self, tmp_path):
        """Should raise FileNotFoundError if no project exists."""
        with pytest.raises(FileNotFoundError, match="未找到项目状态文件"):
            ws.load_state(tmp_path)


class TestValidateState:
    def test_valid_state_passes(self, sample_state):
        errors = ws.validate_state(sample_state)
        assert errors == []

    def test_missing_project_id(self, sample_state):
        bad = dict(sample_state)
        del bad["project_id"]
        errors = ws.validate_state(bad)
        assert len(errors) > 0

    def test_missing_stages(self, sample_state):
        bad = dict(sample_state)
        del bad["stages"]
        errors = ws.validate_state(bad)
        assert len(errors) > 0

    def test_corrupt_yaml_file(self, tmp_paper_project):
        """Should handle non-YAML content gracefully when loading."""
        pw_dir = tmp_paper_project / ".paper-workflow"
        pw_dir.mkdir(parents=True, exist_ok=True)
        (pw_dir / "state.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
        # Config must also exist for load_state to not raise FileNotFoundError
        (pw_dir / "config.yaml").write_text("project_id: test\n", encoding="utf-8")

        with pytest.raises(yaml.YAMLError):
            ws.load_state(tmp_paper_project)


class TestAtomicWrite:
    def test_atomic_write_does_not_corrupt_on_crash(self, tmp_paper_project, monkeypatch):
        """If write fails mid-way, the original state.yaml should be intact."""
        pw_dir = tmp_paper_project / ".paper-workflow"
        pw_dir.mkdir(parents=True, exist_ok=True)
        config_path = pw_dir / "config.yaml"
        config_path.write_text("project_id: test\n", encoding="utf-8")

        # Write an initial state
        original_state = {
            "schema_version": 1,
            "project_id": "test-001",
            "paper_type": "course_paper",
            "current_stage": "requirements",
            "stages": {},
            "overrides": [],
        }
        ws.save_state(original_state, tmp_paper_project)

        # Read back to confirm it was saved
        state_path = pw_dir / "state.yaml"
        original_content = state_path.read_text(encoding="utf-8")

        # Now simulate a failure during write by monkeypatching os.replace
        original_replace = __import__("os").replace

        def failing_replace(src, dst):
            raise OSError("Simulated write failure")

        monkeypatch.setattr("os.replace", failing_replace)

        new_state = dict(original_state)
        new_state["project_id"] = "test-002-modified"

        with pytest.raises(OSError, match="Simulated"):
            ws.save_state(new_state, tmp_paper_project)

        # Original file should still contain the old data
        current_content = state_path.read_text(encoding="utf-8")
        assert current_content == original_content


class TestGetStage:
    def test_get_existing_stage(self, sample_state):
        stage = ws.get_stage(sample_state, "requirements")
        assert stage is not None
        assert stage["status"] == "pending"

    def test_get_nonexistent_stage(self, sample_state):
        assert ws.get_stage(sample_state, "nonexistent") is None

    def test_is_stage_done(self, sample_state):
        sample_state["stages"]["requirements"]["status"] = "done"
        assert ws.is_stage_done(sample_state, "requirements") is True

    def test_is_stage_skipped_counts_as_done(self, sample_state):
        sample_state["stages"]["literature_search"]["status"] = "skipped"
        assert ws.is_stage_done(sample_state, "literature_search") is True

    def test_get_stages_by_status(self, sample_state):
        pending = ws.get_stages_by_status(sample_state, "pending")
        assert "requirements" in pending  # pending in sample_state

    def test_list_stages(self, sample_state):
        stages = ws.list_stages(sample_state)
        assert len(stages) == 17
        assert stages[0] == "requirements"
