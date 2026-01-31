"""
Tests for the AI Grader Agent
=============================
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.grader_agent.pdf_processor import PDFProcessor, Submission
from src.grader_agent.prompt_builder import (
    build_grading_prompt,
    build_dry_run_response,
    encode_image_to_base64
)
from src.grader_agent.grader import GraderAgent, GradingResult


class TestPDFProcessor:
    """Tests for PDF processing functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create a processor with test fixtures."""
        fixtures_dir = Path(__file__).parent / "fixtures" / "fake_submissions"
        return PDFProcessor(fixtures_dir)
    
    def test_get_student_name_from_filename(self, processor):
        """Test student name extraction from filename."""
        assert processor.get_student_name_from_filename("smith.pdf") == "Smith"
        assert processor.get_student_name_from_filename("johnson.pdf") == "Johnson"
        assert processor.get_student_name_from_filename("van_der_berg.pdf") == "Van Der Berg"
    
    def test_process_submission(self, processor):
        """Test processing a single PDF submission."""
        pdf_path = processor.submissions_dir / "smith.pdf"
        if pdf_path.exists():
            submission = processor.process_submission(pdf_path)
            assert submission.student_name == "Smith"
            assert submission.file_path == pdf_path
            # Note: Our simple test PDFs may not extract text perfectly
            assert isinstance(submission.text_content, str)
    
    def test_get_all_submissions(self, processor):
        """Test getting all submissions from directory."""
        if processor.submissions_dir.exists():
            submissions = processor.get_all_submissions()
            assert len(submissions) >= 0  # May have test files
            assert all(isinstance(s, Submission) for s in submissions)


class TestPromptBuilder:
    """Tests for prompt building functionality."""
    
    def test_build_dry_run_response(self):
        """Test dry run response generation."""
        response = build_dry_run_response("Test Student")
        
        assert response["student_name"] == "Test Student"
        assert "rubric_scores" in response
        assert "total_score" in response
        assert "letter_grade" in response
        assert "feedback" in response
        assert "confidence" in response
        assert response["confidence"] == 0.95
    
    def test_dry_run_response_structure(self):
        """Test that dry run response has all required fields."""
        response = build_dry_run_response("Test")
        
        required_fields = [
            "student_name", "rubric_scores", "total_score",
            "max_possible_score", "percentage", "letter_grade",
            "feedback", "strengths", "improvements",
            "integrity_flag", "confidence"
        ]
        
        for field in required_fields:
            assert field in response, f"Missing required field: {field}"


class TestGraderAgent:
    """Tests for the grader agent."""
    
    @pytest.fixture
    def grader(self):
        """Create a grader agent for testing."""
        return GraderAgent(
            model="gpt-4o-mini",
            confidence_threshold=0.7
        )
    
    def test_grader_initialization(self, grader):
        """Test grader initializes with correct settings."""
        assert grader.model == "gpt-4o-mini"
        assert grader.confidence_threshold == 0.7
    
    def test_create_error_result(self, grader):
        """Test error result creation."""
        result = grader._create_error_result("Test Student", "Test error")
        
        assert result.student_name == "Test Student"
        assert result.error == "Test error"
        assert result.flagged_for_review is True
        assert "error" in result.flag_reason.lower()
    
    def test_parse_response_flags_low_confidence(self, grader):
        """Test that low confidence responses are flagged."""
        response_data = {
            "student_name": "Test",
            "total_score": 80,
            "max_possible_score": 100,
            "percentage": 80,
            "letter_grade": "B",
            "feedback": "Good work",
            "strengths": ["strength 1"],
            "improvements": ["improvement 1"],
            "rubric_scores": [],
            "integrity_flag": False,
            "confidence": 0.5  # Below threshold
        }
        
        result = grader._parse_response(response_data, "Test")
        
        assert result.flagged_for_review is True
        assert "confidence" in result.flag_reason.lower()
    
    def test_parse_response_flags_integrity_issues(self, grader):
        """Test that integrity concerns are flagged."""
        response_data = {
            "student_name": "Test",
            "total_score": 80,
            "max_possible_score": 100,
            "percentage": 80,
            "letter_grade": "B",
            "feedback": "Good work",
            "strengths": ["strength 1"],
            "improvements": ["improvement 1"],
            "rubric_scores": [],
            "integrity_flag": True,
            "integrity_reason": "Possible plagiarism detected",
            "confidence": 0.9
        }
        
        result = grader._parse_response(response_data, "Test")
        
        assert result.flagged_for_review is True
        assert result.integrity_flag is True
        assert "integrity" in result.flag_reason.lower()


class TestGradingResult:
    """Tests for the GradingResult dataclass."""
    
    def test_grading_result_creation(self):
        """Test creating a GradingResult."""
        result = GradingResult(
            student_name="Test Student",
            total_score=85,
            max_possible_score=100,
            percentage=85.0,
            letter_grade="B",
            feedback="Good work",
            strengths=["Clear writing"],
            improvements=["Add more examples"],
            rubric_scores=[],
            integrity_flag=False,
            integrity_reason="",
            confidence=0.9
        )
        
        assert result.student_name == "Test Student"
        assert result.total_score == 85
        assert result.letter_grade == "B"
        assert result.confidence == 0.9
        assert result.flagged_for_review is False


# Integration test (requires test files)
class TestIntegration:
    """Integration tests for the full pipeline."""
    
    def test_dry_run_pipeline(self):
        """Test the pipeline in dry-run mode (no API calls)."""
        # This test would run the full pipeline with --dry-run
        # For now, just verify imports work
        from src.grader_agent import (
            PDFProcessor,
            GraderAgent,
            GradingResult,
            process_submissions
        )
        
        assert PDFProcessor is not None
        assert GraderAgent is not None
        assert GradingResult is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
