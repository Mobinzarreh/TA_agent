"""
Grader Agent Module
===================
Single GPT agent that grades submissions using vision API.
Processes rubric image + submission text → structured JSON output.
"""

import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from openai import OpenAI
from dotenv import load_dotenv
import os

from .pdf_processor import Submission
from .prompt_builder import (
    build_grading_prompt,
    build_dry_run_response,
    GRADING_OUTPUT_SCHEMA
)


@dataclass
class GradingResult:
    """Result of grading a single submission."""
    student_name: str
    total_score: float
    max_possible_score: float
    percentage: float
    letter_grade: str
    feedback: str
    strengths: list[str]
    improvements: list[str]
    rubric_scores: list[dict]
    integrity_flag: bool
    integrity_reason: str
    confidence: float
    flagged_for_review: bool = False
    flag_reason: str = ""
    raw_response: dict = field(default_factory=dict)
    error: Optional[str] = None


class GraderAgent:
    """
    AI Grader Agent using OpenAI's vision API.
    
    Processes student submissions against a rubric image and returns
    structured grading results.
    """
    
    def __init__(
        self,
        model: str = "gpt-5-mini",
        max_tokens: int = 2000,
        temperature: float = 0.0,
        confidence_threshold: float = 0.7,
        max_retries: int = 2
    ):
        """
        Initialize the grader agent.
        
        Args:
            model: OpenAI model to use (must support vision)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (lower = more consistent)
            confidence_threshold: Flag for review if confidence below this
            max_retries: Number of retries for failed API calls
        """
        # Load environment variables
        load_dotenv()
        
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.confidence_threshold = confidence_threshold
        self.max_retries = max_retries
        
    def grade_submission(
        self,
        submission: Submission,
        rubric_image_path: Path,
        additional_instructions: Optional[str] = None,
        dry_run: bool = False
    ) -> GradingResult:
        """
        Grade a single student submission.
        
        Args:
            submission: Processed submission object
            rubric_image_path: Path to the rubric image
            additional_instructions: Optional extra instructions
            dry_run: If True, return mock response without API call
            
        Returns:
            GradingResult object
        """
        # Handle extraction failures
        if not submission.extraction_success:
            return GradingResult(
                student_name=submission.student_name,
                total_score=0,
                max_possible_score=0,
                percentage=0,
                letter_grade="",
                feedback="",
                strengths=[],
                improvements=[],
                rubric_scores=[],
                integrity_flag=False,
                integrity_reason="",
                confidence=0,
                flagged_for_review=True,
                flag_reason=f"PDF extraction failed: {submission.error_message}",
                error=submission.error_message
            )
        
        # Dry run mode - return mock response
        if dry_run:
            mock_response = build_dry_run_response(submission.student_name)
            return self._parse_response(mock_response, submission.student_name)
        
        # Build the prompt
        system_prompt, user_content = build_grading_prompt(
            student_name=submission.student_name,
            submission_text=submission.text_content,
            rubric_image_path=rubric_image_path,
            additional_instructions=additional_instructions
        )
        
        # Call the API with retries
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    max_completion_tokens=self.max_tokens,
                    temperature=self.temperature,
                    response_format={"type": "json_object"}
                )
                
                # Parse the response
                response_text = response.choices[0].message.content
                response_data = json.loads(response_text)
                
                return self._parse_response(response_data, submission.student_name)
                
            except json.JSONDecodeError as e:
                if attempt == self.max_retries:
                    return self._create_error_result(
                        submission.student_name,
                        f"Failed to parse API response as JSON: {e}"
                    )
                time.sleep(1)
                
            except Exception as e:
                if attempt == self.max_retries:
                    return self._create_error_result(
                        submission.student_name,
                        f"API call failed: {e}"
                    )
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def _parse_response(self, response_data: dict, student_name: str) -> GradingResult:
        """
        Parse API response into GradingResult object.
        
        Args:
            response_data: Parsed JSON response
            student_name: Student's name (fallback)
            
        Returns:
            GradingResult object
        """
        try:
            # Extract fields with defaults
            confidence = response_data.get("confidence", 0.5)
            integrity_flag = response_data.get("integrity_flag", False)
            integrity_reason = response_data.get("integrity_reason", "")
            
            # Determine if flagged for review
            flagged_for_review = False
            flag_reason = ""
            
            if confidence < self.confidence_threshold:
                flagged_for_review = True
                flag_reason = f"Low confidence score: {confidence:.2f}"
            elif integrity_flag:
                flagged_for_review = True
                flag_reason = f"Academic integrity concern: {integrity_reason}"
            
            return GradingResult(
                student_name=response_data.get("student_name", student_name),
                total_score=response_data.get("total_score", 0),
                max_possible_score=response_data.get("max_possible_score", 100),
                percentage=response_data.get("percentage", 0),
                letter_grade=response_data.get("letter_grade", ""),
                feedback=response_data.get("feedback", ""),
                strengths=response_data.get("strengths", []),
                improvements=response_data.get("improvements", []),
                rubric_scores=response_data.get("rubric_scores", []),
                integrity_flag=integrity_flag,
                integrity_reason=integrity_reason,
                confidence=confidence,
                flagged_for_review=flagged_for_review,
                flag_reason=flag_reason,
                raw_response=response_data
            )
            
        except Exception as e:
            return self._create_error_result(student_name, f"Failed to parse response: {e}")
    
    def _create_error_result(self, student_name: str, error_message: str) -> GradingResult:
        """Create an error result for failed grading."""
        return GradingResult(
            student_name=student_name,
            total_score=0,
            max_possible_score=0,
            percentage=0,
            letter_grade="",
            feedback="",
            strengths=[],
            improvements=[],
            rubric_scores=[],
            integrity_flag=False,
            integrity_reason="",
            confidence=0,
            flagged_for_review=True,
            flag_reason=f"Grading error: {error_message}",
            error=error_message
        )
    
    def test_connection(self) -> bool:
        """
        Test the OpenAI API connection.
        
        Returns:
            True if connection successful
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'OK' if you can read this."}],
                max_completion_tokens=10
            )
            return "ok" in response.choices[0].message.content.lower()
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
