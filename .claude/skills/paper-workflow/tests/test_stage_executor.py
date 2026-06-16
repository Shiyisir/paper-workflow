"""Test stage_executor.py: contract loader, done conditions, artifact logging, dispatcher."""
import json, sys
from pathlib import Path
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import stage_executor as se


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "test-project"
    root.mkdir(parents=True)
    (root / ".paper-workflow").mkdir()
    (root / "manuscript").mkdir()
    (root / "literature").mkdir()
    (root / "outputs" / "qa").mkdir(parents=True)
    (root / "outputs" / "latest").mkdir(parents=True)
    return root


class TestContractLoader:
    def test_load_known_contract(self):
        c = se.load_contract("literature_dedup")
        assert c["stage_id"] == "literature_dedup"
        assert c["executor_type"] == "script"

    def test_load_skill_handoff_contract(self):
        c = se.load_contract("outline")
        assert c["stage_id"] == "outline"
        assert c["executor_type"] == "skill_handoff"
        assert "handoff_done" in c
        assert "stage_done" in c

    def test_load_unknown_stage(self):
        with pytest.raises(FileNotFoundError, match="Contract not found"):
            se.load_contract("nonexistent_stage")

    def test_list_contracts_count(self):
        assert len(se.list_contracts()) == 17

    def test_script_count(self):
        assert len(se.get_contracts_by_type("script")) == 4

    def test_hybrid_count(self):
        assert len(se.get_contracts_by_type("hybrid")) == 1

    def test_handoff_count(self):
        assert len(se.get_contracts_by_type("skill_handoff")) == 6

    def test_manual_count(self):
        assert len(se.get_contracts_by_type("manual")) == 6

    def test_distribution_total(self):
        total = (len(se.get_contracts_by_type("script")) + len(se.get_contracts_by_type("hybrid"))
                 + len(se.get_contracts_by_type("skill_handoff")) + len(se.get_contracts_by_type("manual")))
        assert total == 17

    def test_validate_contract_passes(self):
        c = se.load_contract("literature_dedup")
        assert se.validate_contract(c) == []

    def test_literature_search_has_handoff_fields(self):
        c = se.load_contract("literature_search")
        assert "handoff_done" in c
        assert "stage_done" in c
        assert c["has_waiting_state"] is True


class TestDoneConditions:
    def test_file_exists_true(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "literature" / "dedup-report.md").write_text("ok", encoding="utf-8")
        ok, unmet = se.check_done_conditions("literature_dedup", root)
        assert ok is True

    def test_file_exists_false(self, tmp_path):
        root = _make_project(tmp_path)
        ok, unmet = se.check_done_conditions("literature_dedup", root)
        assert ok is False

    def test_file_exists_empty_fails(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "literature" / "dedup-report.md").write_text("", encoding="utf-8")
        ok, unmet = se.check_done_conditions("literature_dedup", root)
        assert ok is False

    def test_record_count_gt(self, tmp_path):
        root = _make_project(tmp_path)
        cat = root / "literature" / "catalog.jsonl"
        cat.write_text(json.dumps({"citekey":"a"})+"\n"+json.dumps({"citekey":"b"})+"\n", encoding="utf-8")
        slog = root / ".paper-workflow" / "search-log.jsonl"
        slog.write_text(json.dumps({"query":"test"})+"\n", encoding="utf-8")
        ok, unmet = se.check_done_conditions("literature_search", root)
        assert ok is True

    def test_record_count_zero_fails(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "literature" / "catalog.jsonl").write_text("", encoding="utf-8")
        ok, unmet = se.check_done_conditions("literature_search", root)
        assert ok is False

    def test_csv_has_rows_true(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "literature" / "evidence-matrix.csv").write_text("section,citekey\ntest,c1\n", encoding="utf-8")
        cc = root / "citations" / "claim-citation-map.csv"
        cc.parent.mkdir(parents=True, exist_ok=True)
        cc.write_text("claim_id,section,claim_text\nC001,methods,test\n", encoding="utf-8")
        ok, unmet = se.check_done_conditions("evidence_matrix", root)
        assert ok is True

    def test_csv_has_rows_false(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "literature" / "evidence-matrix.csv").write_text("section,citekey\n", encoding="utf-8")
        ok, unmet = se.check_done_conditions("evidence_matrix", root)
        assert ok is False

    def test_no_cite_needed_clean(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "manuscript" / "main.md").write_text("# Title\n\n[@test2024]\n", encoding="utf-8")
        ok, unmet = se.check_done_conditions("writing", root)
        assert ok is True

    def test_cite_needed_detected(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "manuscript" / "main.md").write_text("# Title\n\n[CITE NEEDED]\n", encoding="utf-8")
        from stage_executor import _evaluate_condition
        assert _evaluate_condition("no_unresolved_cite_needed:manuscript/main.md", root) is False

    def test_qa_errors_zero(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "outputs" / "qa" / "qa-report-v001.md").write_text("**Errors**: 0\n", encoding="utf-8")
        from stage_executor import _evaluate_condition
        assert _evaluate_condition("qa_errors == 0", root) is True

    def test_qa_errors_nonzero(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "outputs" / "qa" / "qa-report-v001.md").write_text("**Errors**: 3\n", encoding="utf-8")
        from stage_executor import _evaluate_condition
        assert _evaluate_condition("qa_errors == 0", root) is False

    def test_unknown_condition_raises(self, tmp_path):
        root = _make_project(tmp_path)
        from stage_executor import _evaluate_condition
        with pytest.raises(ValueError, match="Unrecognized condition"):
            _evaluate_condition("unknown:test", root)

    def test_check_handoff_done(self, tmp_path):
        root = _make_project(tmp_path)
        hd = root / ".paper-workflow" / "handoffs"
        hd.mkdir(parents=True, exist_ok=True)
        (hd / "outline.json").write_text('{"stage_id":"outline"}', encoding="utf-8")
        ok, unmet = se.check_handoff_done("outline", root)
        assert ok is True

    def test_check_handoff_done_missing(self, tmp_path):
        root = _make_project(tmp_path)
        ok, unmet = se.check_handoff_done("outline", root)
        assert ok is False

    def test_non_skill_handoff_handoff_always_true(self, tmp_path):
        root = _make_project(tmp_path)
        ok, unmet = se.check_handoff_done("literature_dedup", root)
        assert ok is True


class TestArtifactLogging:
    def test_log_creates_manifest(self, tmp_path):
        root = _make_project(tmp_path)
        se.log_artifacts(root, "formatting", ["out.docx"], "render.py")
        m = root / ".paper-workflow" / "artifact-manifest.jsonl"
        assert m.exists()
        e = json.loads(m.read_text(encoding="utf-8").strip().split("\n")[0])
        assert e["stage_id"] == "formatting"
        assert e["executor"] == "render.py"

    def test_log_appends(self, tmp_path):
        root = _make_project(tmp_path)
        se.log_artifacts(root, "a", ["a1"], "e1")
        se.log_artifacts(root, "b", ["b1"], "e2")
        lines = (root / ".paper-workflow" / "artifact-manifest.jsonl").read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_log_creates_pw_dir(self, tmp_path):
        root = tmp_path / "new"
        root.mkdir()
        se.log_artifacts(root, "test", ["x"], "exe")
        assert (root / ".paper-workflow" / "artifact-manifest.jsonl").exists()


class TestDispatcher:
    def _setup(self, tmp_path):
        root = _make_project(tmp_path)
        state = {"project_id": "test", "current_stage": "requirements", "stages": {}, "overrides": []}
        config = {"project_id": "test", "search_mode": "standard"}
        return root, state, config

    def test_script_stub(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("literature_dedup", root, state, config)
        assert r["executed"] is False
        assert r["executor_type"] == "script"
        assert r["recommended_status"] == "in_progress"

    def test_handoff_returns_waiting(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("outline", root, state, config)
        assert r["recommended_status"] == "waiting_for_user"
        assert r["handoff_generated"] is True

    def test_manual_returns_waiting(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("research_design", root, state, config)
        assert r["recommended_status"] == "waiting_for_user"

    def test_hybrid_stub(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("citation_verification", root, state, config)
        assert r["executor_type"] == "hybrid"
        assert r["recommended_status"] == "in_progress"

    def test_unknown_blocked(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("nonexistent", root, state, config)
        assert r["executor_type"] == "unknown"
        assert r["recommended_status"] == "blocked"

    def test_does_not_write_state(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        sp = root / ".paper-workflow" / "state.yaml"
        if sp.exists():
            sp.unlink()
        se.execute_stage("outline", root, state, config)
        assert not sp.exists()


class TestM2Integration:
    def test_chain(self, tmp_path):
        root = _make_project(tmp_path)
        state = {"project_id": "t"}
        config = {"project_id": "t"}
        c = se.load_contract("formatting")
        assert c["executor_type"] == "script"
        ok, _ = se.check_done_conditions("formatting", root)
        assert ok is False
        r = se.execute_stage("formatting", root, state, config)
        assert r["executor_type"] == "script"

    def test_all_17_dispatch(self, tmp_path):
        root = _make_project(tmp_path)
        state = {"project_id": "t"}
        config = {"project_id": "t"}
        for c in se.list_contracts():
            r = se.execute_stage(c["stage_id"], root, state, config)
            assert r["stage_id"] == c["stage_id"]
            assert r["executor_type"] != "unknown"
            assert "recommended_status" in r
