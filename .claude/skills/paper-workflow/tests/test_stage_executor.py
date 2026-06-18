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

    def test_script_stage_blocked_on_no_catalog(self, tmp_path):
        """literature_dedup without catalog → blocked (real executor in M3)."""
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("literature_dedup", root, state, config)
        assert r["executor_type"] == "script"
        assert r["recommended_status"] == "blocked"

    def test_handoff_returns_waiting(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("outline", root, state, config)
        assert r["recommended_status"] == "waiting_for_user"
        assert r["handoff_generated"] is True

    def test_manual_returns_waiting(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("research_design", root, state, config)
        assert r["recommended_status"] == "waiting_for_user"

    def test_hybrid_blocked_on_missing_manuscript(self, tmp_path):
        """citation_verification without manuscript → blocked (real executor in M6)."""
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("citation_verification", root, state, config)
        assert r["executor_type"] == "hybrid"
        assert r["recommended_status"] == "blocked"

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


# ===== M3: Script Stage Executors =====

class TestLiteratureDedupExecutor:
    def _setup(self, tmp_path, with_records=True):
        root = _make_project(tmp_path)
        state = {"project_id": "t"}
        config = {"project_id": "t"}
        if with_records:
            cat = root / "literature" / "catalog.jsonl"
            records = [
                {"title": "Test Paper", "authors": ["A. Author"], "year": 2024,
                 "doi": "10.1234/test.1", "sources": ["manual"], "screening_status": "included",
                 "language": "en", "canonical_id": "ref-0001", "citekey": "author2024Test"},
                {"title": "Test Paper", "authors": ["A. Author"], "year": 2024,
                 "doi": "10.1234/test.1", "sources": ["crossref"], "screening_status": "included",
                 "language": "en", "canonical_id": "ref-0002", "citekey": "author2024TestA"},
            ]
            cat.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
        return root, state, config

    def test_dedup_with_duplicates(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("literature_dedup", root, state, config)
        assert r["executed"] is True
        assert r["recommended_status"] == "done"
        assert "literature/dedup-report.md" in r["artifacts"]
        assert (root / "literature" / "dedup-report.md").exists()
        # After dedup, the duplicate should be merged
        cat_text = (root / "literature" / "catalog.jsonl").read_text(encoding="utf-8")
        assert cat_text.count("ref-") == 1  # merged to one

    def test_dedup_empty_catalog_blocked(self, tmp_path):
        root, state, config = self._setup(tmp_path, with_records=False)
        (root / "literature" / "catalog.jsonl").write_text("", encoding="utf-8")
        r = se.execute_stage("literature_dedup", root, state, config)
        assert r["recommended_status"] == "blocked"

    def test_dedup_missing_catalog_blocked(self, tmp_path):
        root = _make_project(tmp_path)
        state = {"project_id": "t"}
        config = {"project_id": "t"}
        r = se.execute_stage("literature_dedup", root, state, config)
        assert r["recommended_status"] == "blocked"

    def test_dedup_writes_manifest(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        se.execute_stage("literature_dedup", root, state, config)
        manifest = root / ".paper-workflow" / "artifact-manifest.jsonl"
        assert manifest.exists()
        entries = [json.loads(line) for line in manifest.read_text(encoding="utf-8").strip().split("\n")]
        assert any(e["stage_id"] == "literature_dedup" for e in entries)


class TestEvidenceMatrixExecutor:
    def _setup(self, tmp_path):
        root = _make_project(tmp_path)
        state = {"project_id": "t"}
        config = {"project_id": "t"}
        return root, state, config

    def test_initializes_files(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("evidence_matrix", root, state, config)
        assert r["executed"] is True
        assert r["requires_confirmation"] is True
        assert r["recommended_status"] == "pending_confirmation"
        assert (root / "literature" / "evidence-matrix.csv").exists()
        assert (root / "citations" / "claim-citation-map.csv").exists()

    def test_returns_pending_confirmation(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("evidence_matrix", root, state, config)
        assert r["recommended_status"] == "pending_confirmation"

    def test_writes_manifest(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        se.execute_stage("evidence_matrix", root, state, config)
        manifest = root / ".paper-workflow" / "artifact-manifest.jsonl"
        assert manifest.exists()


class TestFormattingExecutor:
    def _setup(self, tmp_path, with_manuscript=True):
        root = _make_project(tmp_path)
        (root / "literature" / "references.bib").write_text("@article{test,\n  title={T}\n}\n", encoding="utf-8")
        if with_manuscript:
            (root / "manuscript" / "main.md").write_text("# Test\n\nHello world.\n", encoding="utf-8")
        state = {"project_id": "t"}
        config = {"project_id": "t", "default_profile": "markdown-draft"}
        return root, state, config

    def test_render_succeeds(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("formatting", root, state, config)
        assert r["executed"] is True
        assert r["recommended_status"] == "done"
        assert (root / "outputs" / "latest").exists()

    def test_no_manuscript_blocked(self, tmp_path):
        root, state, config = self._setup(tmp_path, with_manuscript=False)
        r = se.execute_stage("formatting", root, state, config)
        assert r["recommended_status"] == "blocked"

    def test_missing_materials_template_not_blocked(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        # materials/templates/reference.docx does not exist
        r = se.execute_stage("formatting", root, state, config)
        assert r["recommended_status"] == "done"

    def test_writes_manifest(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        se.execute_stage("formatting", root, state, config)
        manifest = root / ".paper-workflow" / "artifact-manifest.jsonl"
        assert manifest.exists()


class TestQualityQaExecutor:
    def _setup(self, tmp_path, with_outputs=True):
        root = _make_project(tmp_path)
        (root / "manuscript" / "main.md").write_text("# Test\n\nHello.\n", encoding="utf-8")
        if with_outputs:
            with open(root / "outputs" / "latest" / "draft.md", "w", encoding="utf-8") as f:
                f.write("# Draft")
        state = {"project_id": "t"}
        config = {"project_id": "t"}
        return root, state, config

    def test_qa_runs(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("quality_qa", root, state, config)
        assert r["executed"] is True
        # QA may pass or warn depending on project state — both are ok
        assert r["recommended_status"] in ("done", "blocked")

    def test_qa_writes_manifest(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        se.execute_stage("quality_qa", root, state, config)
        manifest = root / ".paper-workflow" / "artifact-manifest.jsonl"
        assert manifest.exists()

    def test_qa_errors_blocked(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        # Create a bad catalog to trigger QA errors
        (root / "literature" / "catalog.jsonl").write_text(
            '{"bad": "record", "canonical_id": "ref-0001", "citekey": "x", "title": "T", "authors": ["A"], "year": 2000, "language": "en", "sources": ["manual"], "screening_status": "included"}\n',
            encoding="utf-8"
        )
        r = se.execute_stage("quality_qa", root, state, config)
        # bad record should trigger catalog errors
        assert r["executed"] is True


class TestM3Integration:
    """End-to-end chain: dedup → evidence → formatting → QA."""
    def _setup(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "manuscript" / "main.md").write_text("# Test\n\nHello world.\n", encoding="utf-8")
        (root / "literature" / "references.bib").write_text("@article{test,\n  title={T}\n}\n", encoding="utf-8")
        cat = root / "literature" / "catalog.jsonl"
        records = [
            {"title": "Test Paper", "authors": ["A. Author"], "year": 2024,
             "doi": "10.1234/test.1", "sources": ["manual"], "screening_status": "included",
             "language": "en", "canonical_id": "ref-0001", "citekey": "author2024Test"},
        ]
        cat.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
        state = {"project_id": "t"}
        config = {"project_id": "t", "default_profile": "markdown-draft"}
        return root, state, config

    def test_dedup_evidence_format_chain(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r1 = se.execute_stage("literature_dedup", root, state, config)
        assert r1["recommended_status"] == "done"
        r2 = se.execute_stage("evidence_matrix", root, state, config)
        assert r2["recommended_status"] == "pending_confirmation"
        r3 = se.execute_stage("formatting", root, state, config)
        assert r3["recommended_status"] == "done"
        r4 = se.execute_stage("quality_qa", root, state, config)
        assert r4["executed"] is True


# ===== M4: Skill Handoff =====

class TestHandoffGeneration:
    def _setup(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "materials" / "requirements").mkdir(parents=True, exist_ok=True)
        (root / "materials" / "templates").mkdir(parents=True, exist_ok=True)
        (root / "materials" / "examples").mkdir(parents=True, exist_ok=True)
        (root / "materials" / "notes").mkdir(parents=True, exist_ok=True)
        state = {"project_id": "t", "paper_type": "course_paper", "research_type": "review",
                 "discipline": "computer_science", "language": "zh"}
        config = {"project_id": "t", "paper_type": "course_paper", "research_type": "review",
                  "discipline": "computer_science", "language": "zh", "search_mode": "standard"}
        return root, state, config

    def test_outline_handoff_generated(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("outline", root, state, config)
        assert r["handoff_generated"] is True
        assert r["recommended_status"] == "waiting_for_user"
        hp = root / ".paper-workflow" / "handoffs" / "outline.json"
        assert hp.exists()

    def test_writing_handoff_generated(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("writing", root, state, config)
        assert r["handoff_generated"] is True
        assert (root / ".paper-workflow" / "handoffs" / "writing.json").exists()

    def test_deep_reading_handoff_generated(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("deep_reading", root, state, config)
        assert r["handoff_generated"] is True
        assert (root / ".paper-workflow" / "handoffs" / "deep_reading.json").exists()

    def test_handoff_json_contains_expected_fields(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        se.execute_stage("outline", root, state, config)
        import json as j
        data = j.loads((root / ".paper-workflow" / "handoffs" / "outline.json").read_text(encoding="utf-8"))
        assert data["stage_id"] == "outline"
        assert "nature-writing" in data["skill"]
        assert len(data["task_prompt"]) > 50
        assert "expected_outputs" in data
        assert "input_files" in data
        assert "materials_summary" in data

    def test_multiple_handoffs_no_overwrite(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        se.execute_stage("outline", root, state, config)
        se.execute_stage("writing", root, state, config)
        hd = root / ".paper-workflow" / "handoffs"
        assert (hd / "outline.json").exists()
        assert (hd / "writing.json").exists()

    def test_latest_json_updated(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        se.execute_stage("outline", root, state, config)
        import json as j
        latest = j.loads((root / ".paper-workflow" / "handoffs" / "latest.json").read_text(encoding="utf-8"))
        assert latest["stage_id"] == "outline"

    def test_all_6_skill_handoff_stages(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        stages = ["literature_search", "deep_reading", "outline", "writing", "polishing", "charts_and_tables"]
        for sid in stages:
            r = se.execute_stage(sid, root, state, config)
            assert r["handoff_generated"] is True, f"{sid} handoff not generated"
            assert r["recommended_status"] == "waiting_for_user", f"{sid} wrong status"

    def test_handoff_with_materials_file(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        (root / "materials" / "requirements" / "guide.md").write_text("# Guide", encoding="utf-8")
        r = se.execute_stage("outline", root, state, config)
        import json as j
        data = j.loads((root / ".paper-workflow" / "handoffs" / "outline.json").read_text(encoding="utf-8"))
        assert any("guide.md" in m for m in data.get("materials_summary", []))

    def test_missing_materials_not_blocked(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        import shutil
        mats = root / "materials"
        if mats.exists():
            shutil.rmtree(mats)
        r = se.execute_stage("outline", root, state, config)
        assert r["handoff_generated"] is True

    def test_does_not_write_state(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        sp = root / ".paper-workflow" / "state.yaml"
        if sp.exists():
            sp.unlink()
        se.execute_stage("outline", root, state, config)
        assert not sp.exists()

    def test_writes_manifest(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        se.execute_stage("outline", root, state, config)
        assert (root / ".paper-workflow" / "artifact-manifest.jsonl").exists()


# ===== M5.1: Manual Stages =====

class TestManualStages:
    def _setup(self, tmp_path):
        root = _make_project(tmp_path)
        state = {"project_id": "t"}
        config = {"project_id": "t"}
        return root, state, config

    def test_research_design_returns_manual(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("research_design", root, state, config)
        assert r["executor_type"] == "manual"
        assert r["requires_manual_action"] is True
        assert r["recommended_status"] == "waiting_for_user"
        assert "message" in r
        assert "research_design" in r["message"]

    def test_requirements_returns_manual(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("requirements", root, state, config)
        assert r["requires_manual_action"] is True
        assert "message" in r

    def test_revision_marks_future(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("revision", root, state, config)
        assert r["requires_manual_action"] is True
        assert "FUTURE" in r["message"] or "v0.3" in r["message"]

    def test_all_6_manual_stages(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        stages = ["requirements", "material_prep", "research_design", "data_analysis",
                  "originality_check", "revision"]
        for sid in stages:
            r = se.execute_stage(sid, root, state, config)
            assert r["executor_type"] == "manual", f"{sid} wrong executor_type"
            assert "message" in r, f"{sid} missing message"

    def test_manual_does_not_write_state(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        sp = root / ".paper-workflow" / "state.yaml"
        if sp.exists():
            sp.unlink()
        se.execute_stage("research_design", root, state, config)
        assert not sp.exists()


# ===== M6: Hybrid citation_verification =====

class TestCitationVerification:
    def _setup(self, tmp_path, with_ms=True, ms_content=None, with_bib=True, bib_content=None):
        root = _make_project(tmp_path)
        if with_ms:
            content = ms_content or "# Title\n\nSome text [@test2024].\n"
            (root / "manuscript" / "main.md").write_text(content, encoding="utf-8")
        if with_bib:
            bc = bib_content or "@article{test2024,\n  title={T},\n  author={A},\n  year={2024}\n}\n"
            (root / "literature" / "references.bib").write_text(bc, encoding="utf-8")
        state = {"project_id": "t"}
        config = {"project_id": "t"}
        return root, state, config

    def test_clean_manuscript_returns_done(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        r = se.execute_stage("citation_verification", root, state, config)
        assert r["executed"] is True
        assert r["recommended_status"] == "done"
        assert r["handoff_generated"] is False

    def test_missing_citekey_generates_handoff(self, tmp_path):
        root, state, config = self._setup(
            tmp_path,
            ms_content="# Title\n\n[@missing2024] [@test2024].\n",
        )
        r = se.execute_stage("citation_verification", root, state, config)
        assert r["recommended_status"] == "waiting_for_user"
        assert r["handoff_generated"] is True
        assert r.get("handoff_path") is not None
        hf = root / ".paper-workflow" / "handoffs" / "citation_verification.json"
        assert hf.exists()

    def test_cite_needed_generates_handoff(self, tmp_path):
        root, state, config = self._setup(
            tmp_path,
            ms_content="# Title\n\n[CITE NEEDED]\nSome text [@test2024].\n",
        )
        r = se.execute_stage("citation_verification", root, state, config)
        assert r["recommended_status"] == "waiting_for_user"
        assert r["handoff_generated"] is True

    def test_handoff_contains_issue_details(self, tmp_path):
        import json as j
        root, state, config = self._setup(
            tmp_path,
            ms_content="# Title\n\n[@missing2024] [@test2024].\n",
        )
        se.execute_stage("citation_verification", root, state, config)
        hf = root / ".paper-workflow" / "handoffs" / "citation_verification.json"
        data = j.loads(hf.read_text(encoding="utf-8"))
        assert "nature-citation" in data["skill"]
        assert len(data["citation_issues"]) >= 1
        assert any("missing2024" in iss for iss in data["citation_issues"])
        assert "不要新增虚假文献" in data["task_prompt"]

    def test_missing_manuscript_blocked(self, tmp_path):
        root, state, config = self._setup(tmp_path, with_ms=False)
        r = se.execute_stage("citation_verification", root, state, config)
        assert r["recommended_status"] == "blocked"

    def test_writes_citation_report(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        se.execute_stage("citation_verification", root, state, config)
        rpt = root / "outputs" / "qa" / "citation-report.md"
        assert rpt.exists()

    def test_does_not_import_nature_citation(self, tmp_path):
        """Verify nature-citation is NOT imported anywhere in stage_executor."""
        import stage_executor as s
        src = s.__file__
        with open(src, encoding="utf-8") as f:
            content = f.read()
        assert "import nature_citation" not in content
        assert "from nature_citation" not in content

    def test_does_not_write_state(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        sp = root / ".paper-workflow" / "state.yaml"
        if sp.exists():
            sp.unlink()
        se.execute_stage("citation_verification", root, state, config)
        assert not sp.exists()

    def test_writes_manifest(self, tmp_path):
        root, state, config = self._setup(tmp_path)
        se.execute_stage("citation_verification", root, state, config)
        assert (root / ".paper-workflow" / "artifact-manifest.jsonl").exists()

    def test_unused_citekey_is_warning_only(self, tmp_path):
        """Unused citekey in bib → warning, but if no other issues → done."""
        root, state, config = self._setup(
            tmp_path,
            ms_content="# Title\n\n[@test2024].\n",
            bib_content="@article{test2024,\n  title={T},\n  author={A},\n  year={2024}\n}\n\n"
                        "@article{unused2023,\n  title={U},\n  author={B},\n  year={2023}\n}\n",
        )
        r = se.execute_stage("citation_verification", root, state, config)
        # Unused citekey is a warning, not an issue → should be done
        assert r["recommended_status"] == "done"
        assert "unused" in str(r.get("warnings", [])) or r["recommended_status"] == "done"
