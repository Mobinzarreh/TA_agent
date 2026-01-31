"""
PDF Processor Module
====================
Extracts text content from student submission PDFs.
Handles lastname.pdf naming convention.
"""

import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class Submission:
    """Represents a student submission."""
    student_name: str  # Extracted from filename (lastname)
    file_path: Path
    text_content: str
    page_count: int
    extraction_success: bool
    error_message: Optional[str] = None


class PDFProcessor:
    """Process PDF submissions and extract text content."""
    
    def __init__(self, submissions_dir: Path):
        """
        Initialize the PDF processor.
        
        Args:
            submissions_dir: Path to directory containing student PDFs
        """
        self.submissions_dir = Path(submissions_dir)
        
    def get_student_name_from_filename(self, filename: str) -> str:
        """
        Extract student name from filename.
        Expected format: lastname.pdf
        
        Args:
            filename: PDF filename
            
        Returns:
            Student last name (capitalized)
        """
        # Remove .pdf extension and clean up
        name = Path(filename).stem
        # Handle potential underscores or hyphens
        name = name.replace("_", " ").replace("-", " ")
        # Capitalize properly
        return name.title()
    
    def extract_text_from_pdf(self, pdf_path: Path) -> tuple[str, int]:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
        """
        text_parts = []
        
        with fitz.open(pdf_path) as doc:
            page_count = len(doc)
            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                    
        full_text = "\n\n".join(text_parts)
        return full_text, page_count
    
    def process_submission(self, pdf_path: Path) -> Submission:
        """
        Process a single PDF submission.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Submission object with extracted content
        """
        student_name = self.get_student_name_from_filename(pdf_path.name)
        
        try:
            text_content, page_count = self.extract_text_from_pdf(pdf_path)
            
            if not text_content.strip():
                return Submission(
                    student_name=student_name,
                    file_path=pdf_path,
                    text_content="",
                    page_count=page_count,
                    extraction_success=False,
                    error_message="PDF appears to be empty or contains only images/scans"
                )
            
            return Submission(
                student_name=student_name,
                file_path=pdf_path,
                text_content=text_content,
                page_count=page_count,
                extraction_success=True
            )
            
        except Exception as e:
            return Submission(
                student_name=student_name,
                file_path=pdf_path,
                text_content="",
                page_count=0,
                extraction_success=False,
                error_message=str(e)
            )
    
    def get_all_submissions(self) -> list[Submission]:
        """
        Find and process all PDF submissions in the submissions directory.
        
        Returns:
            List of Submission objects
        """
        submissions = []
        
        if not self.submissions_dir.exists():
            raise FileNotFoundError(f"Submissions directory not found: {self.submissions_dir}")
        
        pdf_files = sorted(self.submissions_dir.glob("*.pdf"))
        
        if not pdf_files:
            raise ValueError(f"No PDF files found in: {self.submissions_dir}")
        
        for pdf_path in pdf_files:
            submission = self.process_submission(pdf_path)
            submissions.append(submission)
            
        return submissions
    
    def get_submission_summary(self, submissions: list[Submission]) -> dict:
        """
        Get summary statistics for processed submissions.
        
        Args:
            submissions: List of processed submissions
            
        Returns:
            Summary dictionary
        """
        successful = [s for s in submissions if s.extraction_success]
        failed = [s for s in submissions if not s.extraction_success]
        
        return {
            "total": len(submissions),
            "successful": len(successful),
            "failed": len(failed),
            "failed_names": [s.student_name for s in failed],
            "failed_reasons": [s.error_message for s in failed]
        }


# Convenience function for quick processing
def process_submissions(submissions_dir: str | Path) -> list[Submission]:
    """
    Process all PDF submissions in a directory.
    
    Args:
        submissions_dir: Path to submissions directory
        
    Returns:
        List of Submission objects
    """
    processor = PDFProcessor(Path(submissions_dir))
    return processor.get_all_submissions()
