"""Test init_project.py."""

import sys
from pathlib import Path

import yaml

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import init_project


def test_generate_project_id():
    assert init_project.generate_project_id("My-Thesis") == "my-thesis"
    assert init_project.generate_project_id("  Test Paper  ") == "test-paper"
    assert init_project.generate_project_id("simple") == "simple"


def test_build_state():
    state = init_project.build_state(
        project_id="test-001",
        paper_type="course_paper",
        research_type="review",
        discipline="computer_science",
        language="zh",
        target_journal=None,
        search_mode="quick",
    )
    assert state["schema_version"] == 1
    assert state["project_id"] == "test-001"
    assert state["current_stage"] == "requirements"
    assert "requirements" in state["stages"]
    assert state["stages"]["requirements"]["status"] == "in_progress"
    # requirements has no dependencies
    assert state["stages"]["requirements"]["depends_on"] == []


def test_build_state_skips_book_report_stages():
    state = init_project.build_state(
        project_id="test-002",
        paper_type="book_report",
        research_type="review",
        discipline="humanities",
        language="zh",
        target_journal=None,
        search_mode="quick",
    )
    # Book reports skip literature and data stages
    assert state["stages"]["literature_search"]["status"] == "skipped"
    assert state["stages"]["deep_reading"]["status"] == "skipped"
    assert state["stages"]["data_analysis"]["status"] == "skipped"
    # But outline is still required
    assert state["stages"]["outline"]["status"] == "pending"


def test_build_config():
    config = init_project.build_config(
        project_id="test-001",
        paper_type="thesis",
        research_type="empirical",
        discipline="engineering",
        language="zh",
        target_journal=None,
        search_mode="standard",
    )
    assert config["project_id"] == "test-001"
    assert config["paper_type"] == "thesis"
    assert config["citation_style"] == "gb-t-7714"  # zh default


def test_build_config_en_defaults_to_apa():
    config = init_project.build_config(
        project_id="test-003",
        paper_type="journal_article",
        research_type="empirical",
        discipline="medicine",
        language="en",
        target_journal="Nature",
        search_mode="standard",
    )
    assert config["citation_style"] == "apa"


def test_project_exists(tmp_paper_project):
    """Empty directory should report no project."""
    assert not init_project.project_exists(tmp_paper_project)


def test_project_exists_detects_state(tmp_paper_project):
    """Directory with state.yaml should be detected."""
    state_file = tmp_paper_project / ".paper-workflow" / "state.yaml"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("schema_version: 1\n")
    assert init_project.project_exists(tmp_paper_project)


def test_init_project_creates_files(tmp_paper_project):
    """Full init should create all required files."""
    params = {
        "project_id": "test-001",
        "paper_type": "course_paper",
        "research_type": "review",
        "discipline": "computer_science",
        "language": "zh",
        "target_journal": None,
        "search_mode": "quick",
    }
    result = init_project.init_project(tmp_paper_project, params)
    assert result is True

    # Check files exist
    assert (tmp_paper_project / ".paper-workflow" / "state.yaml").exists()
    assert (tmp_paper_project / ".paper-workflow" / "config.yaml").exists()
    assert (tmp_paper_project / ".paper-workflow" / "artifact-manifest.jsonl").exists()

    # Check directories exist
    for d in ["manuscript", "literature", "citations", "figures", "tables",
              "outputs/latest", "outputs/qa", "analysis", "materials"]:
        assert (tmp_paper_project / d).is_dir(), f"Missing dir: {d}"

    # Check state.yaml content
    with open(tmp_paper_project / ".paper-workflow" / "state.yaml", encoding="utf-8") as f:
        state = yaml.safe_load(f)
    assert state["project_id"] == "test-001"
    assert len(state["stages"]) == 17


def test_init_project_idempotent(tmp_paper_project):
    """Repeated init without --force should not overwrite."""
    params = {
        "project_id": "test-001",
        "paper_type": "course_paper",
        "research_type": "review",
        "discipline": "computer_science",
        "language": "zh",
        "target_journal": None,
        "search_mode": "quick",
    }
    # First init succeeds
    assert init_project.init_project(tmp_paper_project, params) is True
    # Second init fails (no --force)
    assert init_project.init_project(tmp_paper_project, params) is False


def test_init_project_force_overwrites(tmp_paper_project):
    """--force should allow overwriting."""
    params = {
        "project_id": "test-001",
        "paper_type": "course_paper",
        "research_type": "review",
        "discipline": "computer_science",
        "language": "zh",
        "target_journal": None,
        "search_mode": "quick",
    }
    assert init_project.init_project(tmp_paper_project, params) is True
    assert init_project.init_project(tmp_paper_project, params, force=True) is True


def test_create_directories(tmp_path):
    dirs = init_project.create_directories(tmp_path)
    assert len(dirs) == 16
    for d in dirs:
        assert d.is_dir()
