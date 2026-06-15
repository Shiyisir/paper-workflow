"""Test qa_report.py."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import qa_report as qr

MINI_PAPER = Path(__file__).resolve().parent / "fixtures" / "mini-paper"


class TestRunAllChecks:
    def test_mini_paper_passes_or_warns(self):
        """Clean mini-paper should pass or pass_with_warnings."""
        results = qr.run_all_checks(MINI_PAPER)
        assert results["overall"] in ("passed", "passed_with_warnings", "failed")
        assert "catalog" in results["checks"]
        assert "citations" in results["checks"]
        assert "manuscript" in results["checks"]

    def test_mini_paper_has_summary(self):
        results = qr.run_all_checks(MINI_PAPER)
        assert results["summary"]["checks_run"] >= 3

    def test_catalog_check_succeeds(self):
        results = qr.run_all_checks(MINI_PAPER)
        cat = results["checks"]["catalog"]
        assert cat["status"] in ("passed", "passed_with_warnings")

    def test_docx_tex_skipped_when_no_outputs(self):
        results = qr.run_all_checks(MINI_PAPER)
        # Mini-paper has no outputs/*.docx or *.tex → should be None (skipped)
        assert results["checks"]["docx"] is None
        assert results["checks"]["tex"] is None


class TestGenerateReport:
    def test_generates_report_file(self, tmp_path):
        results = qr.run_all_checks(MINI_PAPER)
        path = tmp_path / "qa-report-v001.md"
        out = qr.generate_qa_report(results, path)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "QA 质量核验报告" in content
        assert "摘要" in content

    def test_report_has_status(self, tmp_path):
        results = qr.run_all_checks(MINI_PAPER)
        path = tmp_path / "report.md"
        out = qr.generate_qa_report(results, path)
        content = out.read_text(encoding="utf-8")
        assert results["overall"] in content

    def test_report_has_section_results(self, tmp_path):
        results = qr.run_all_checks(MINI_PAPER)
        path = tmp_path / "report.md"
        out = qr.generate_qa_report(results, path)
        content = out.read_text(encoding="utf-8")
        assert "catalog" in content.lower()


class TestNextReportVersion:
    def test_first_version(self, tmp_path):
        path = qr._next_report_version(tmp_path)
        assert path.name == "qa-report-v001.md"

    def test_increments(self, tmp_path):
        (tmp_path / "qa-report-v001.md").write_text("")
        (tmp_path / "qa-report-v003.md").write_text("")
        path = qr._next_report_version(tmp_path)
        assert path.name == "qa-report-v004.md"
