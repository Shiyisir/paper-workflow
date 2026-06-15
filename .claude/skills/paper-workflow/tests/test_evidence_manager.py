"""Test evidence_manager.py."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import evidence_manager as em


def _setup_project(tmp_path: Path) -> Path:
    root = tmp_path / "test-project"
    root.mkdir(parents=True)
    (root / ".paper-workflow").mkdir()
    (root / "literature").mkdir(parents=True)
    (root / "citations").mkdir(parents=True)
    return root


class TestEvidenceMatrix:
    def test_init_creates_file_with_header(self, tmp_path):
        root = _setup_project(tmp_path)
        path = em.init_evidence_matrix(root)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "citekey" in content
        assert "usable_sections" in content

    def test_add_and_read_entry(self, tmp_path):
        root = _setup_project(tmp_path)
        em.init_evidence_matrix(root)
        em.add_evidence_entry({
            "citekey": "wang2024Rocky",
            "topic": "rocky desertification",
            "key_finding": "Reduced ESV by 23%",
            "usable_sections": "introduction;literature_review",
            "method": "spatial analysis",
        }, root)

        rows = em._read_csv(em.get_evidence_path(root))
        assert len(rows) == 1
        assert rows[0]["citekey"] == "wang2024Rocky"

    def test_filter_by_section(self, tmp_path):
        root = _setup_project(tmp_path)
        em.init_evidence_matrix(root)
        em.add_evidence_entry({
            "citekey": "wang2024Rocky",
            "topic": "desertification",
            "key_finding": "ESV reduced",
            "usable_sections": "introduction",
        }, root)
        em.add_evidence_entry({
            "citekey": "zhang2023DL",
            "topic": "deep learning",
            "key_finding": "CNN improves accuracy",
            "usable_sections": "methods;results",
        }, root)

        intro = em.get_evidence_for_section("introduction", root)
        assert len(intro) == 1
        assert intro[0]["citekey"] == "wang2024Rocky"

        methods = em.get_evidence_for_section("methods", root)
        assert len(methods) == 1

        # Nonexistent section
        empty = em.get_evidence_for_section("conclusion", root)
        assert empty == []

    def test_filter_by_citekey(self, tmp_path):
        root = _setup_project(tmp_path)
        em.init_evidence_matrix(root)
        em.add_evidence_entry({
            "citekey": "wang2024Rocky",
            "topic": "A",
            "key_finding": "X",
            "usable_sections": "intro",
        }, root)
        em.add_evidence_entry({
            "citekey": "wang2024Rocky",
            "topic": "B",
            "key_finding": "Y",
            "usable_sections": "discussion",
        }, root)

        matches = em.get_evidence_by_citekey("wang2024Rocky", root)
        assert len(matches) == 2

    def test_empty_file_returns_empty(self, tmp_path):
        root = _setup_project(tmp_path)
        assert em.get_evidence_for_section("intro", root) == []
        assert em.get_evidence_by_citekey("nonexistent", root) == []


class TestClaimMap:
    def test_init_creates_file_with_header(self, tmp_path):
        root = _setup_project(tmp_path)
        path = em.init_claim_map(root)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "claim_id" in content
        assert "supporting_citekeys" in content

    def test_add_claim_returns_incremented_id(self, tmp_path):
        root = _setup_project(tmp_path)
        cid1 = em.add_claim({
            "section": "introduction",
            "claim": "Karst desertification is severe",
            "supporting_citekeys": "wang2024Rocky",
            "strength": "strong",
            "verified": "yes",
        }, root)
        assert cid1 == "C001"

        cid2 = em.add_claim({
            "section": "introduction",
            "claim": "Ecosystem services are declining",
            "supporting_citekeys": "zhang2023DL",
            "strength": "medium",
            "verified": "pending",
        }, root)
        assert cid2 == "C002"

    def test_claim_id_continuous_across_files(self, tmp_path):
        root = _setup_project(tmp_path)
        em.add_claim({"section": "intro", "claim": "A", "strength": "strong", "verified": "yes"}, root)
        em.add_claim({"section": "intro", "claim": "B", "strength": "medium", "verified": "pending"}, root)
        em.add_claim({"section": "methods", "claim": "C", "strength": "weak", "verified": "no"}, root)

        all_claims = em.get_all_claims(root)
        ids = [c["claim_id"] for c in all_claims]
        assert ids == ["C001", "C002", "C003"]

    def test_filter_by_section(self, tmp_path):
        root = _setup_project(tmp_path)
        em.add_claim({"section": "introduction", "claim": "A", "strength": "strong", "verified": "yes"}, root)
        em.add_claim({"section": "methods", "claim": "B", "strength": "strong", "verified": "yes"}, root)

        intro = em.get_claims_by_section("introduction", root)
        assert len(intro) == 1
        assert intro[0]["claim_id"] == "C001"

    def test_filter_by_citekey_reverse_lookup(self, tmp_path):
        root = _setup_project(tmp_path)
        em.add_claim({
            "section": "introduction",
            "claim": "Desertification is serious",
            "supporting_citekeys": "wang2024Rocky;zhang2023DL",
            "strength": "strong",
            "verified": "yes",
        }, root)
        em.add_claim({
            "section": "methods",
            "claim": "CNN works well",
            "supporting_citekeys": "zhang2023DL",
            "strength": "medium",
            "verified": "pending",
        }, root)

        # zhang2023DL used in 2 claims
        matches = em.get_claims_by_citekey("zhang2023DL", root)
        assert len(matches) == 2

        # wang2024Rocky used in 1 claim
        matches = em.get_claims_by_citekey("wang2024Rocky", root)
        assert len(matches) == 1

        # No match
        matches = em.get_claims_by_citekey("nonexistent", root)
        assert matches == []

    def test_invalid_strength_raises(self, tmp_path):
        root = _setup_project(tmp_path)
        with pytest.raises(ValueError, match="strength"):
            em.add_claim({
                "section": "intro",
                "claim": "Test",
                "strength": "invalid",
                "verified": "yes",
            }, root)

    def test_invalid_verified_raises(self, tmp_path):
        root = _setup_project(tmp_path)
        with pytest.raises(ValueError, match="verified"):
            em.add_claim({
                "section": "intro",
                "claim": "Test",
                "strength": "strong",
                "verified": "maybe",
            }, root)

    def test_semicolon_citekeys_parsed(self, tmp_path):
        root = _setup_project(tmp_path)
        em.add_claim({
            "section": "discussion",
            "claim": "Multiple sources support this",
            "supporting_citekeys": "wang2024Rocky; zhang2023DL; li2022Study",
            "strength": "strong",
            "verified": "yes",
        }, root)

        # Check each citekey can be found
        for ck in ["wang2024Rocky", "zhang2023DL", "li2022Study"]:
            matches = em.get_claims_by_citekey(ck, root)
            assert len(matches) >= 1, f"citekey {ck} not found"
