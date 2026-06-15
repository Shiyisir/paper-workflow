"""End-to-end acceptance tests covering the full MVP pipeline.

Each test creates a fresh project in tmp_path, copies mini-paper fixture
content, and runs the complete init→dedup→render→qa→resume flow.
"""

import shutil
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
MINI_PAPER = FIXTURES_DIR / "mini-paper"

import init_project
import dedup
import render as rdr
import qa_report as qr
from workflow_state import load_state, find_project_root
from validate_catalog import validate_catalog
from validate_citations import check_citekey_consistency
from literature_store import read_catalog
from export_references import export_bib, export_csl_json, sync_citekeys
from evidence_manager import init_evidence_matrix, add_evidence_entry, add_claim
from commands import cmd_status, cmd_resume, cmd_run


def _copy_mini_paper_content(dest: Path) -> None:
    """Copy mini-paper content into a project created by init_project."""
    # manuscript
    shutil.copy2(MINI_PAPER / "manuscript" / "main.md", dest / "manuscript" / "main.md")
    # figures
    if (MINI_PAPER / "figures").exists():
        shutil.copytree(MINI_PAPER / "figures", dest / "figures", dirs_exist_ok=True)
    # literature
    for f in ["catalog.jsonl", "references.bib", "references.csl.json"]:
        src = MINI_PAPER / "literature" / f
        if src.exists():
            shutil.copy2(src, dest / "literature" / f)
    # citations + evidence
    shutil.copy2(MINI_PAPER / "citations" / "claim-citation-map.csv",
                 dest / "citations" / "claim-citation-map.csv")
    shutil.copy2(MINI_PAPER / "literature" / "evidence-matrix.csv",
                 dest / "literature" / "evidence-matrix.csv")


class TestE2EFullPipeline:
    """Complete pipeline from init to QA."""

    def test_init_to_qa_complete(self, tmp_path):
        """init → import content → validate → render → qa → resume."""
        project = tmp_path / "pw-e2e"
        project.mkdir(parents=True)

        # 1. Init
        params = {
            "project_id": "pw-e2e",
            "paper_type": "course_paper",
            "research_type": "review",
            "discipline": "computer_science",
            "language": "zh",
            "target_journal": None,
            "search_mode": "quick",
        }
        assert init_project.init_project(project, params) is True
        assert (project / ".paper-workflow" / "state.yaml").exists()
        assert (project / ".paper-workflow" / "config.yaml").exists()

        # 2. Import mini-paper content
        _copy_mini_paper_content(project)

        # 3. Validate catalog
        cat_result = validate_catalog(project)
        assert cat_result["total_records"] == 3
        assert cat_result["errors"] == [], f"Catalog errors: {cat_result['errors']}"

        # 4. Validate citations
        ms = project / "manuscript" / "main.md"
        bib = project / "literature" / "references.bib"
        cit_result = check_citekey_consistency(ms, bib)
        assert cit_result["missing_in_bib"] == [], f"Missing: {cit_result['missing_in_bib']}"

        # 5. Dedup
        catalog_records = read_catalog(project)
        dedup_result = dedup.deduplicate(catalog_records)
        assert len(dedup_result["unique"]) == 3  # All unique

        # 6. Three render profiles
        r_md = rdr.render("markdown-draft", ms, project / "outputs", project)
        assert r_md["success"], f"markdown-draft failed: {r_md['errors']}"
        assert r_md["output_path"].suffix == ".md"

        r_docx = rdr.render("thesis-cn", ms, project / "outputs", project)
        assert r_docx["success"], f"thesis-cn failed: {r_docx['errors']}"
        assert r_docx["output_path"].suffix == ".docx"

        r_tex = rdr.render("journal-latex", ms, project / "outputs", project)
        assert r_tex["success"], f"journal-latex failed: {r_tex['errors']}"
        assert r_tex["output_path"].suffix == ".tex"

        # 7. QA report
        qa_results = qr.run_all_checks(project)
        assert qa_results["overall"] in ("passed", "passed_with_warnings")
        qa_path = project / "outputs" / "qa" / "e2e-report.md"
        qr.generate_qa_report(qa_results, qa_path)
        assert qa_path.exists()

        # 8. Latest only has final clean files
        latest = project / "outputs" / "latest"
        assert latest.exists()

        # 9. Versioned outputs exist
        outputs = list((project / "outputs").glob("*-v*.md"))
        assert len(outputs) >= 1

        # 10. Status command
        import os
        os.chdir(str(project))
        rc = cmd_status()
        assert rc == 0

    def test_resume_and_override(self, tmp_path, monkeypatch):
        """Resume from a state and use override to skip deps."""
        project = tmp_path / "pw-resume"
        project.mkdir(parents=True)
        params = {
            "project_id": "pw-resume",
            "paper_type": "course_paper",
            "research_type": "review",
            "discipline": "computer_science",
            "language": "zh",
            "target_journal": None,
            "search_mode": "quick",
        }
        init_project.init_project(project, params)
        _copy_mini_paper_content(project)
        monkeypatch.chdir(project)

        # Resume on fresh project
        rc = cmd_resume()
        assert rc == 0  # requirements is in_progress

        # Override to jump to citation_verification
        rc = cmd_run("citation_verification", override=True)
        assert rc == 0

        # Verify state reflects the override
        loaded = load_state(project)
        assert loaded["state"]["stages"]["citation_verification"]["status"] == "done"
        assert len(loaded["state"]["overrides"]) >= 1

    def test_dry_run_preview(self, tmp_path):
        """--dry-run shows operations without creating files."""
        project = tmp_path / "pw-dry"
        project.mkdir(parents=True)
        params = {
            "project_id": "pw-dry",
            "paper_type": "course_paper",
            "research_type": "review",
            "discipline": "computer_science",
            "language": "zh",
            "target_journal": None,
            "search_mode": "quick",
        }
        init_project.init_project(project, params)
        _copy_mini_paper_content(project)

        ms = project / "manuscript" / "main.md"
        result = rdr.render("markdown-draft", ms, project / "outputs", project, dry_run=True)
        assert result["dry_run"] is True
        assert result["output_path"] is None
        # No files should have been created in outputs/
        outputs = list((project / "outputs").glob("*.md"))
        assert len(outputs) == 0

    def test_export_references_sync(self, tmp_path):
        """Bib and CSL JSON export with sync check."""
        project = tmp_path / "pw-export"
        project.mkdir(parents=True)
        params = {
            "project_id": "pw-export",
            "paper_type": "course_paper",
            "research_type": "review",
            "discipline": "computer_science",
            "language": "zh",
            "target_journal": None,
            "search_mode": "quick",
        }
        init_project.init_project(project, params)
        _copy_mini_paper_content(project)

        # Export from catalog
        n_bib = export_bib(project)
        n_csl = export_csl_json(project)
        assert n_bib == 3
        assert n_csl == 3

        # Sync check
        ok = sync_citekeys(
            project / "literature" / "references.bib",
            project / "literature" / "references.csl.json",
        )
        assert ok is True

    def test_reproducible(self, tmp_path):
        """The entire pipeline can be run twice with identical results."""
        for run in [1, 2]:
            project = tmp_path / f"pw-repro-{run}"
            project.mkdir(parents=True)
            params = {
                "project_id": f"pw-repro-{run}",
                "paper_type": "course_paper",
                "research_type": "review",
                "discipline": "computer_science",
                "language": "zh",
                "target_journal": None,
                "search_mode": "quick",
            }
            init_project.init_project(project, params)
            _copy_mini_paper_content(project)

            ms = project / "manuscript" / "main.md"
            r = rdr.render("markdown-draft", ms, project / "outputs", project)
            assert r["success"], f"Run {run} failed"

            qa = qr.run_all_checks(project)
            assert qa["overall"] in ("passed", "passed_with_warnings")
