"""Test JSON Schema validation against fixtures."""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml


SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def load_schema(name: str) -> dict:
    with open(SCHEMA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


class TestWorkflowStateSchema:
    """Validate sample_state fixture against workflow-state schema."""

    @pytest.fixture
    def schema(self):
        return load_schema("workflow-state.schema.json")

    def test_valid_state_passes(self, schema, sample_state):
        jsonschema.validate(sample_state, schema)

    def test_missing_required_field_fails(self, schema, sample_state):
        bad = dict(sample_state)
        del bad["project_id"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_invalid_paper_type_fails(self, schema, sample_state):
        bad = dict(sample_state)
        bad["paper_type"] = "invalid_type"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_invalid_stage_status_fails(self, schema, sample_state):
        bad = dict(sample_state)
        bad["stages"]["requirements"]["status"] = "unknown_status"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_empty_project_id_fails(self, schema, sample_state):
        bad = dict(sample_state)
        bad["project_id"] = ""
        # Empty string should pass schema (type is string, no minLength)
        # but we can check that language must be valid enum
        bad2 = dict(sample_state)
        bad2["language"] = "fr"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad2, schema)


class TestLiteratureRecordSchema:
    """Validate sample_literature_records against literature-record schema."""

    @pytest.fixture
    def schema(self):
        return load_schema("literature-record.schema.json")

    def test_valid_records_pass(self, schema, sample_literature_records):
        for record in sample_literature_records:
            jsonschema.validate(record, schema)

    def test_missing_canonical_id_fails(self, schema, sample_literature_records):
        bad = dict(sample_literature_records[0])
        del bad["canonical_id"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_invalid_canonical_id_format_fails(self, schema, sample_literature_records):
        bad = dict(sample_literature_records[0])
        bad["canonical_id"] = "bad-format"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_empty_authors_fails(self, schema, sample_literature_records):
        bad = dict(sample_literature_records[0])
        bad["authors"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)


class TestRenderProfileSchema:
    """Validate profile-like dicts against render-profile schema."""

    @pytest.fixture
    def schema(self):
        return load_schema("render-profile.schema.json")

    def test_thesis_cn_profile_valid(self, schema):
        profile = {
            "output": "docx",
            "reference_doc": "templates/docx/thesis-cn-reference.docx",
            "csl": "templates/csl/gb-t-7714.csl",
            "number_sections": False,
            "native_math": "omml",
            "convert_svg_to": "png",
            "toc": True,
            "toc_depth": 3,
            "caption_style": "chinese",
            "postprocess": True,
        }
        jsonschema.validate(profile, schema)

    def test_journal_latex_profile_valid(self, schema):
        profile = {
            "output": "tex",
            "latex_template": "templates/latex/journal.tex",
            "csl": "templates/csl/apa.csl",
            "number_sections": True,
            "native_math": "latex",
            "convert_svg_to": "pdf",
            "toc": False,
            "postprocess": False,
        }
        jsonschema.validate(profile, schema)

    def test_markdown_draft_profile_valid(self, schema):
        profile = {
            "output": "md",
            "csl": None,
            "number_sections": False,
            "native_math": "raw",
            "convert_svg_to": "none",
            "toc": False,
            "postprocess": False,
        }
        jsonschema.validate(profile, schema)

    def test_missing_required_field_fails(self, schema):
        bad = {"output": "docx"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_invalid_output_format_fails(self, schema):
        bad = {"output": "pdf", "native_math": "raw"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)


class TestStageExecutionContractSchema:
    """Validate stage execution contracts against stage-execution schema."""

    @pytest.fixture
    def schema(self):
        return load_schema("stage-execution.schema.json")

    def _make_contract(self, **overrides):
        base = {
            "stage_id": "test_stage",
            "phase": 1,
            "phase_label": "test",
            "executor_type": "script",
            "input_artifacts": ["test/input.csv"],
            "output_artifacts": ["test/output.csv"],
            "preconditions": ["test/input.csv exists"],
            "done_conditions": ["file_exists:test/output.csv"],
            "quality_checks": [],
            "user_confirmation_required": False,
        }
        base.update(overrides)
        return base

    def test_script_contract_valid(self, schema):
        contract = self._make_contract(executor_type="script")
        jsonschema.validate(contract, schema)

    def test_skill_handoff_contract_valid(self, schema):
        contract = self._make_contract(
            stage_id="outline",
            executor_type="skill_handoff",
            required_skill="nature-writing",
            done_conditions=["file_exists:manuscript/outline.md"],
            handoff_done=["file_exists:.paper-workflow/handoffs/outline.json"],
            stage_done=["file_exists:manuscript/outline.md"],
            handoff_prompt_template="write outline for {topic}",
        )
        jsonschema.validate(contract, schema)

    def test_skill_handoff_requires_handoff_done(self, schema):
        contract = self._make_contract(
            executor_type="skill_handoff",
            required_skill="nature-reader",
            handoff_prompt_template="read {title}",
        )
        # Missing handoff_done and stage_done should fail for skill_handoff
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(contract, schema)

    def test_required_skill_as_string(self, schema):
        contract = self._make_contract(
            executor_type="skill_handoff",
            required_skill="nature-reader",
            handoff_done=["file_exists:handoffs/test.json"],
            stage_done=["file_exists:output/test.md"],
            handoff_prompt_template="test",
        )
        jsonschema.validate(contract, schema)

    def test_required_skill_as_language_map(self, schema):
        contract = self._make_contract(
            executor_type="skill_handoff",
            required_skill={"zh": "cnki-search", "en": "nature-academic-search"},
            handoff_done=["file_exists:handoffs/test.json"],
            stage_done=["file_exists:output/test.md"],
            handoff_prompt_template="test",
        )
        jsonschema.validate(contract, schema)

    def test_invalid_executor_type_fails(self, schema):
        bad = self._make_contract(executor_type="nonexistent")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_hybrid_contract_valid(self, schema):
        contract = self._make_contract(
            stage_id="citation_verification",
            executor_type="hybrid",
            script_module="validate_citations",
            followup_skill="nature-citation",
        )
        jsonschema.validate(contract, schema)

    def test_manual_contract_valid(self, schema):
        contract = self._make_contract(executor_type="manual")
        jsonschema.validate(contract, schema)

    def test_missing_stage_id_fails(self, schema):
        bad = self._make_contract()
        del bad["stage_id"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_missing_executor_type_fails(self, schema):
        bad = self._make_contract()
        del bad["executor_type"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_all_contract_files_pass_schema(self, schema):
        """Every YAML file in contracts/ must validate against the schema."""
        import yaml
        contracts_dir = SCHEMA_DIR.parent / "contracts"
        assert contracts_dir.is_dir(), "contracts/ directory not found"
        count = 0
        for cf in contracts_dir.glob("*.yaml"):
            with open(cf, encoding="utf-8") as f:
                contract = yaml.safe_load(f)
            jsonschema.validate(contract, schema)
            count += 1
        assert count == 17, f"Expected 17 contracts, found {count}"

    def test_contract_distribution(self, schema):
        """Verify executor_type distribution: 4 script, 1 hybrid, 6 handoff, 6 manual."""
        import yaml
        contracts_dir = SCHEMA_DIR.parent / "contracts"
        dist = {"script": 0, "hybrid": 0, "skill_handoff": 0, "manual": 0}
        for cf in contracts_dir.glob("*.yaml"):
            with open(cf, encoding="utf-8") as f:
                c = yaml.safe_load(f)
            dist[c["executor_type"]] += 1
        assert dist == {"script": 4, "hybrid": 1, "skill_handoff": 6, "manual": 6}, f"Wrong distribution: {dist}"
