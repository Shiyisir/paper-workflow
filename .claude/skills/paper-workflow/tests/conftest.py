"""Shared fixtures for paper-workflow tests."""

import json
import shutil
from pathlib import Path

import pytest


@pytest.fixture
def tmp_paper_project(tmp_path: Path) -> Path:
    """Create a minimal paper project directory under a temp path."""
    project_root = tmp_path / "test-paper"
    project_root.mkdir(parents=True)

    # Create runtime directories
    for d in [
        "manuscript",
        "literature",
        "citations",
        "figures",
        "tables",
        "outputs/latest",
        "outputs/qa",
        ".paper-workflow",
        "analysis",
    ]:
        (project_root / d).mkdir(parents=True)

    return project_root


@pytest.fixture
def sample_config() -> dict:
    """Return a valid config.yaml dict."""
    return {
        "project_id": "test-paper-001",
        "paper_type": "course_paper",
        "research_type": "review",
        "discipline": "computer_science",
        "language": "zh",
        "target_journal": None,
        "search_mode": "quick",
        "search_capabilities": {
            "cnki_search": "available",
            "cnki_download": "available",
            "scopus": "unavailable",
            "crossref": "available",
            "pubmed": "available",
            "arxiv": "available",
            "sciencedirect": "unavailable",
        },
    }


@pytest.fixture
def sample_state() -> dict:
    """Return a valid state.yaml dict with all 17 stages."""
    stages = {}
    stage_ids = [
        "requirements", "material_prep", "literature_search", "literature_dedup",
        "deep_reading", "evidence_matrix", "research_design", "data_analysis",
        "charts_and_tables", "outline", "writing", "citation_verification",
        "polishing", "formatting", "originality_check", "quality_qa", "revision",
    ]
    for sid in stage_ids:
        stages[sid] = {
            "status": "pending",
            "depends_on": [],
            "started_at": None,
            "completed_at": None,
            "qa_status": "pending",
            "qa_report": None,
            "artifacts": [],
            "blockers": [],
        }

    return {
        "schema_version": 1,
        "project_id": "test-paper-001",
        "paper_type": "course_paper",
        "research_type": "review",
        "discipline": "computer_science",
        "language": "zh",
        "target_journal": None,
        "current_stage": "requirements",
        "stages": stages,
        "overrides": [],
    }


@pytest.fixture
def sample_literature_records() -> list[dict]:
    """Return 3 valid literature records, including 1 duplicate pair."""
    return [
        {
            "canonical_id": "ref-0001",
            "citekey": "wang2024RockyDesertification",
            "title": "Rocky desertification impacts on ecosystem services in karst regions",
            "authors": ["Wang, X.", "Li, Y.", "Zhang, H."],
            "year": 2024,
            "doi": "10.1016/j.ecoser.2024.101650",
            "journal": "Ecosystem Services",
            "volume": "68",
            "pages": "101650",
            "abstract": "Karst rocky desertification is a severe environmental problem.",
            "keywords": ["rocky desertification", "ecosystem services", "karst"],
            "language": "en",
            "sources": ["scopus"],
            "fulltext_available": False,
            "fulltext_path": None,
            "related_versions": [],
            "screening_status": "included",
            "screening_notes": "",
        },
        {
            "canonical_id": "ref-0002",
            "citekey": "zhang2023DeepLearningKarst",
            "title": "Deep learning approaches for karst landscape classification",
            "authors": ["Zhang, L.", "Chen, M."],
            "year": 2023,
            "doi": "10.3390/rs15051234",
            "journal": "Remote Sensing",
            "volume": "15",
            "pages": "1234",
            "abstract": "This paper presents a deep learning framework.",
            "keywords": ["deep learning", "karst", "classification"],
            "language": "en",
            "sources": ["crossref"],
            "fulltext_available": True,
            "fulltext_path": None,
            "related_versions": [],
            "screening_status": "included",
            "screening_notes": "",
        },
        {
            "canonical_id": "ref-0003",
            "citekey": "wang2024RockyDesertificationDup",
            "title": "Rocky Desertification Impacts on Ecosystem Services in Karst Regions",
            "authors": ["Wang, X.", "Li, Y.", "Zhang, H."],
            "year": 2024,
            "doi": "https://doi.org/10.1016/j.ecoser.2024.101650",
            "journal": "Ecosystem Services",
            "volume": "68",
            "pages": "101650",
            "abstract": "Same paper with different DOI format.",
            "keywords": ["rocky desertification"],
            "language": "en",
            "sources": ["crossref"],
            "fulltext_available": False,
            "fulltext_path": None,
            "related_versions": [],
            "screening_status": "pending",
            "screening_notes": "",
        },
    ]
