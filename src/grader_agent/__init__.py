"""
Grader Agent Package
====================
AI-powered grading assistant for student submissions.
"""

from .pdf_processor import PDFProcessor, Submission, process_submissions
from .grader import GraderAgent, GradingResult
from .prompt_builder import build_grading_prompt, build_dry_run_response

__all__ = [
    "PDFProcessor",
    "Submission", 
    "process_submissions",
    "GraderAgent",
    "GradingResult",
    "build_grading_prompt",
    "build_dry_run_response"
]

__version__ = "0.1.0"
