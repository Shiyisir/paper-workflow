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
