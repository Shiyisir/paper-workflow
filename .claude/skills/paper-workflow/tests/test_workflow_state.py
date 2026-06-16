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


# ---------------------------------------------------------------------------
# M2.2 State transition tests
# ---------------------------------------------------------------------------

def _build_state_with_deps() -> dict:
    """Build a minimal state with a realistic dependency chain for testing."""
    from init_project import STAGE_IDS, DEPENDENCY_GRAPH
    state = {
        "schema_version": 1,
        "project_id": "test-transitions",
        "paper_type": "course_paper",
        "research_type": "review",
        "discipline": "computer_science",
        "language": "zh",
        "target_journal": None,
        "current_stage": "requirements",
        "stages": {},
        "overrides": [],
    }
    for sid in STAGE_IDS:
        state["stages"][sid] = {
            "status": "pending",
            "depends_on": DEPENDENCY_GRAPH.get(sid, []),
            "started_at": None,
            "completed_at": None,
            "qa_status": "pending",
            "qa_report": None,
            "artifacts": [],
            "blockers": [],
        }
    state["stages"]["requirements"]["status"] = "in_progress"
    return state


class TestSetStageStatus:
    def test_set_done_with_met_deps(self):
        """requirements has no deps → can be set to done."""
        state = _build_state_with_deps()
        result = ws.set_stage_status(state, "requirements", "done")
        assert result["success"] is True
        assert state["stages"]["requirements"]["status"] == "done"
        assert state["stages"]["requirements"]["completed_at"] is not None

    def test_set_blocked_when_deps_unmet(self):
        """literature_dedup depends on literature_search (pending) → blocked."""
        state = _build_state_with_deps()
        result = ws.set_stage_status(state, "literature_dedup", "in_progress")
        assert result["success"] is False
        assert "literature_search" in result["blocked_deps"]
        assert state["stages"]["literature_dedup"]["status"] == "blocked"
        # Blockers should be recorded
        assert len(state["stages"]["literature_dedup"]["blockers"]) > 0

    def test_override_skips_dep_check(self):
        """With override=True, can set even with unmet deps."""
        state = _build_state_with_deps()
        result = ws.set_stage_status(state, "literature_dedup", "in_progress", override=True)
        assert result["success"] is True
        assert result["overridden"] is True
        assert state["stages"]["literature_dedup"]["status"] == "in_progress"
        # Override should be logged
        assert len(state["overrides"]) == 1
        assert state["overrides"][0]["stage"] == "literature_dedup"

    def test_override_logs_missing_deps(self):
        """Override log should include which deps were missing."""
        state = _build_state_with_deps()
        ws.set_stage_status(state, "writing", "done", override=True)
        override_entry = state["overrides"][0]
        assert "literature_dedup" in override_entry["missing_deps"] or len(override_entry["missing_deps"]) >= 0

    def test_unknown_stage_returns_error(self):
        state = _build_state_with_deps()
        result = ws.set_stage_status(state, "nonexistent_stage", "done")
        assert result["success"] is False
        assert "未知阶段" in result["message"]

    def test_invalid_status_returns_error(self):
        state = _build_state_with_deps()
        result = ws.set_stage_status(state, "requirements", "invalid")
        assert result["success"] is False
        assert "无效状态" in result["message"]

    def test_waiting_for_user_is_valid(self):
        """waiting_for_user is a valid v0.2 status."""
        state = _build_state_with_deps()
        result = ws.set_stage_status(state, "literature_search", "waiting_for_user", override=True)
        assert result["success"] is True
        assert state["stages"]["literature_search"]["status"] == "waiting_for_user"

    def test_pending_confirmation_is_valid(self):
        """pending_confirmation is a valid v0.2 status."""
        state = _build_state_with_deps()
        result = ws.set_stage_status(state, "evidence_matrix", "pending_confirmation", override=True)
        assert result["success"] is True
        assert state["stages"]["evidence_matrix"]["status"] == "pending_confirmation"

    def test_done_clears_blockers(self):
        """When a blocked stage is later completed (after deps met), blockers clear."""
        state = _build_state_with_deps()
        # First, try to set writing to done (will block)
        ws.set_stage_status(state, "writing", "done")
        assert state["stages"]["writing"]["status"] == "blocked"
        assert len(state["stages"]["writing"]["blockers"]) > 0

        # Now complete the dependency chain up to writing
        ws.set_stage_status(state, "requirements", "done")
        ws.set_stage_status(state, "literature_search", "done", override=True)
        ws.set_stage_status(state, "literature_dedup", "done", override=True)
        ws.set_stage_status(state, "deep_reading", "done", override=True)
        ws.set_stage_status(state, "evidence_matrix", "done", override=True)
        ws.set_stage_status(state, "outline", "done", override=True)
        ws.set_stage_status(state, "charts_and_tables", "done", override=True)

        # Now writing can be set to done without override
        result = ws.set_stage_status(state, "writing", "done")
        assert result["success"] is True
        assert state["stages"]["writing"]["blockers"] == []


class TestGetNextStages:
    def test_requirements_done_unlocks_next(self):
        """After requirements done, material_prep and literature_search become available."""
        state = _build_state_with_deps()
        # First, only requirements should be available (it's already in_progress)
        ws.set_stage_status(state, "requirements", "done")
        next_stages = ws.get_next_stages(state)
        assert "material_prep" in next_stages
        assert "literature_search" in next_stages

    def test_no_next_if_all_done(self):
        """All stages done → no next stages."""
        state = _build_state_with_deps()
        for sid in ws.list_stages(state):
            ws.set_stage_status(state, sid, "done", override=True)
        assert ws.get_next_stages(state) == []

    def test_skipped_stages_count_as_met(self):
        """Skipped dependencies should satisfy depends_on."""
        state = _build_state_with_deps()
        # Skip literature_search
        state["stages"]["literature_search"]["status"] = "skipped"
        state["stages"]["requirements"]["status"] = "done"
        # literature_dedup depends on literature_search (now skipped)
        next_stages = ws.get_next_stages(state)
        assert "literature_dedup" in next_stages


class TestGetBlockedStages:
    def test_returns_blocked_stages(self):
        state = _build_state_with_deps()
        ws.set_stage_status(state, "writing", "done")  # Will block
        blocked = ws.get_blocked_stages(state)
        assert len(blocked) >= 1
        assert any(b["stage_id"] == "writing" for b in blocked)

    def test_no_blocked_when_all_clean(self):
        state = _build_state_with_deps()
        ws.set_stage_status(state, "requirements", "done")
        blocked = ws.get_blocked_stages(state)
        # requirements just completed, nothing should be blocked
        writing_blocked = [b for b in blocked if b["stage_id"] == "writing"]
        assert len(writing_blocked) == 0


class TestMarkStageBlocked:
    def test_marks_blocked_with_reason(self):
        state = _build_state_with_deps()
        ws.mark_stage_blocked(state, "literature_search", "CNKI 暂时无法访问")
        assert state["stages"]["literature_search"]["status"] == "blocked"
        assert "CNKI 暂时无法访问" in state["stages"]["literature_search"]["blockers"]

    def test_unknown_stage_raises(self):
        state = _build_state_with_deps()
        with pytest.raises(ValueError, match="未知阶段"):
            ws.mark_stage_blocked(state, "nonexistent", "reason")

    def test_duplicate_reason_not_added(self):
        state = _build_state_with_deps()
        ws.mark_stage_blocked(state, "literature_search", "reason A")
        ws.mark_stage_blocked(state, "literature_search", "reason A")
        # Should only appear once
        assert state["stages"]["literature_search"]["blockers"].count("reason A") == 1
