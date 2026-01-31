"""
Prompt Builder Module
=====================
Builds optimized prompts for the grading agent.
Handles rubric image encoding and structured output schema.
"""

import base64
from pathlib import Path
from typing import Optional


# JSON schema for structured grading output
GRADING_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "student_name": {
            "type": "string",
            "description": "The student's name from the submission"
        },
        "rubric_scores": {
            "type": "array",
            "description": "Scores for each rubric criterion",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string", "description": "Name of the rubric criterion"},
                    "max_points": {"type": "number", "description": "Maximum possible points"},
                    "awarded_points": {"type": "number", "description": "Points awarded"},
                    "justification": {"type": "string", "description": "Brief justification for score"}
                },
                "required": ["criterion", "max_points", "awarded_points", "justification"]
            }
        },
        "total_score": {
            "type": "number",
            "description": "Total points awarded (sum of all criteria)"
        },
        "max_possible_score": {
            "type": "number",
            "description": "Maximum possible total points"
        },
        "percentage": {
            "type": "number",
            "description": "Percentage score (0-100)"
        },
        "letter_grade": {
            "type": "string",
            "enum": ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F"],
            "description": "Letter grade based on percentage"
        },
        "feedback": {
            "type": "string",
            "description": "Personalized feedback paragraph for the student (2-4 sentences)"
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of 2-3 specific strengths in the submission"
        },
        "improvements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of 2-3 specific areas for improvement"
        },
        "integrity_flag": {
            "type": "boolean",
            "description": "True if there are academic integrity concerns"
        },
        "integrity_reason": {
            "type": "string",
            "description": "Explanation of integrity concerns (only if flagged)"
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in the grading accuracy (0.0-1.0)"
        }
    },
    "required": [
        "student_name", "rubric_scores", "total_score", "max_possible_score",
        "percentage", "letter_grade", "feedback", "strengths", "improvements",
        "integrity_flag", "confidence"
    ]
}


# System prompt for the grading agent
SYSTEM_PROMPT = """You are an expert teaching assistant grading student assignments. Your role is to:

1. **Analyze the rubric image** carefully to understand all grading criteria and point allocations
2. **Evaluate the student submission** against each rubric criterion
3. **Assign fair and consistent scores** with clear justifications
4. **Provide constructive feedback** that helps students learn and improve

## Grading Principles:
- Be FAIR and CONSISTENT - grade based solely on the rubric criteria
- Be SPECIFIC - reference actual content from the submission in your justifications
- Be CONSTRUCTIVE - feedback should help students understand how to improve
- Be ACCURATE - double-check your point calculations

## Academic Integrity:
Flag submissions if you notice:
- Text that appears copied from common sources without citation
- Inconsistent writing quality suggesting parts were not written by the student
- Suspiciously similar phrasing to known sources
- Any other red flags warranting instructor review

Do NOT flag for:
- Poor grammar or writing quality (this is a grading criterion, not integrity issue)
- Using course materials appropriately
- Common phrases or standard terminology

## Confidence Score Guidelines:
- 0.9-1.0: Clear submission, rubric criteria clearly met/not met
- 0.7-0.9: Some ambiguity but confident in assessment
- 0.5-0.7: Significant ambiguity, recommend human review
- Below 0.5: Unable to grade reliably, requires human review

## Letter Grade Scale:
A: 90-100% | A-: 87-89% | B+: 83-86% | B: 80-82% | B-: 77-79%
C+: 73-76% | C: 70-72% | C-: 67-69% | D+: 63-66% | D: 60-62% | D-: 57-59% | F: Below 57%
"""


def encode_image_to_base64(image_path: Path) -> str:
    """
    Encode an image file to base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_image_media_type(image_path: Path) -> str:
    """
    Get the media type for an image based on extension.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Media type string (e.g., 'image/png')
    """
    extension = image_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    return media_types.get(extension, "image/png")


def build_grading_prompt(
    student_name: str,
    submission_text: str,
    rubric_image_path: Path,
    additional_instructions: Optional[str] = None
) -> tuple[str, list[dict]]:
    """
    Build the complete grading prompt with rubric image and submission text.
    
    Args:
        student_name: Name of the student
        submission_text: Extracted text from student's PDF
        rubric_image_path: Path to the rubric image
        additional_instructions: Optional extra grading instructions
        
    Returns:
        Tuple of (system_prompt, messages_content)
    """
    # Encode rubric image
    rubric_base64 = encode_image_to_base64(rubric_image_path)
    media_type = get_image_media_type(rubric_image_path)
    
    # Build user message content (multimodal: image + text)
    user_content = [
        {
            "type": "text",
            "text": f"## Grading Task\n\nPlease grade the following student submission using the rubric image provided.\n\n**Student Name:** {student_name}"
        },
        {
            "type": "text",
            "text": "## Rubric\nAnalyze this rubric image to understand all grading criteria:"
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{rubric_base64}",
                "detail": "high"  # High detail for reading rubric text
            }
        },
        {
            "type": "text",
            "text": f"## Student Submission\n\n{submission_text}"
        }
    ]
    
    # Add additional instructions if provided
    if additional_instructions:
        user_content.append({
            "type": "text",
            "text": f"## Additional Grading Instructions\n\n{additional_instructions}"
        })
    
    # Add output format reminder
    user_content.append({
        "type": "text",
        "text": """## Required Output

Provide your grading response as a JSON object with the following structure:
- rubric_scores: Array of {criterion, max_points, awarded_points, justification}
- total_score, max_possible_score, percentage
- letter_grade (A through F)
- feedback (2-4 sentences of personalized feedback)
- strengths (2-3 bullet points)
- improvements (2-3 bullet points)
- integrity_flag (true/false)
- integrity_reason (only if flagged)
- confidence (0.0-1.0)

Be thorough in analyzing the rubric and fair in your assessment."""
    })
    
    return SYSTEM_PROMPT, user_content


def build_dry_run_response(student_name: str) -> dict:
    """
    Build a mock response for dry-run mode.
    
    Args:
        student_name: Name of the student
        
    Returns:
        Mock grading response dictionary
    """
    return {
        "student_name": student_name,
        "rubric_scores": [
            {
                "criterion": "Content Quality",
                "max_points": 40,
                "awarded_points": 35,
                "justification": "[DRY RUN] Mock score for testing"
            },
            {
                "criterion": "Organization",
                "max_points": 30,
                "awarded_points": 25,
                "justification": "[DRY RUN] Mock score for testing"
            },
            {
                "criterion": "Writing Quality",
                "max_points": 30,
                "awarded_points": 28,
                "justification": "[DRY RUN] Mock score for testing"
            }
        ],
        "total_score": 88,
        "max_possible_score": 100,
        "percentage": 88.0,
        "letter_grade": "B+",
        "feedback": "[DRY RUN] This is a mock feedback response for testing the pipeline. No actual grading was performed.",
        "strengths": [
            "[DRY RUN] Mock strength 1",
            "[DRY RUN] Mock strength 2"
        ],
        "improvements": [
            "[DRY RUN] Mock improvement 1",
            "[DRY RUN] Mock improvement 2"
        ],
        "integrity_flag": False,
        "integrity_reason": "",
        "confidence": 0.95
    }
