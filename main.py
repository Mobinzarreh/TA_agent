#!/usr/bin/env python3
"""
AI Grader Agent - Main Entry Point
===================================
Processes student PDF submissions against a rubric image,
generating grades and feedback exported to CSV.

Usage:
    python main.py --assignment assignment_1
    python main.py --assignment assignment_1 --dry-run
    python main.py --assignment assignment_1 --batch-start 20
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

import yaml
from dotenv import load_dotenv

from src.grader_agent import (
    PDFProcessor,
    GraderAgent,
    GradingResult,
    process_submissions
)


def load_config(config_path: Path) -> dict:
    """Load YAML configuration file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def setup_output_files(output_dir: Path, assignment_name: str) -> tuple[Path, Path, Path]:
    """
    Setup output file paths with timestamps.
    
    Returns:
        Tuple of (grades_csv, flagged_csv, audit_log) paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    grades_csv = output_dir / f"grades_{timestamp}.csv"
    flagged_csv = output_dir / f"flagged_{timestamp}.csv"
    audit_log = output_dir / f"grading_log_{timestamp}.jsonl"
    
    return grades_csv, flagged_csv, audit_log


def write_grades_csv(results: list[GradingResult], output_path: Path):
    """Write grading results to CSV file."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            "Student Name",
            "Total Score",
            "Max Score",
            "Percentage",
            "Letter Grade",
            "Feedback",
            "Strengths",
            "Improvements",
            "Confidence"
        ])
        
        # Data rows
        for result in results:
            writer.writerow([
                result.student_name,
                result.total_score,
                result.max_possible_score,
                f"{result.percentage:.1f}",
                result.letter_grade,
                result.feedback,
                " | ".join(result.strengths),
                " | ".join(result.improvements),
                f"{result.confidence:.2f}"
            ])


def write_flagged_csv(results: list[GradingResult], output_path: Path):
    """Write flagged submissions to CSV for human review."""
    flagged = [r for r in results if r.flagged_for_review]
    
    if not flagged:
        print("✓ No submissions flagged for review")
        return
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            "Student Name",
            "Total Score",
            "Letter Grade",
            "Feedback",
            "Flag Reason",
            "Integrity Flag",
            "Integrity Reason",
            "Confidence",
            "Error"
        ])
        
        # Data rows
        for result in flagged:
            writer.writerow([
                result.student_name,
                result.total_score,
                result.letter_grade,
                result.feedback,
                result.flag_reason,
                result.integrity_flag,
                result.integrity_reason,
                f"{result.confidence:.2f}",
                result.error or ""
            ])
    
    print(f"⚠ {len(flagged)} submissions flagged for review → {output_path}")


def write_audit_log(result: GradingResult, log_path: Path):
    """Append grading result to JSONL audit log (privacy-safe)."""
    # Create audit entry (excluding raw submission text for privacy)
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "student_id": result.student_name,  # In production, use student ID
        "total_score": result.total_score,
        "max_possible_score": result.max_possible_score,
        "percentage": result.percentage,
        "letter_grade": result.letter_grade,
        "rubric_scores": result.rubric_scores,
        "confidence": result.confidence,
        "integrity_flag": result.integrity_flag,
        "flagged_for_review": result.flagged_for_review,
        "flag_reason": result.flag_reason,
        "error": result.error
    }
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_entry) + "\n")


def print_progress(current: int, total: int, student_name: str, result: GradingResult):
    """Print progress update."""
    status = "✓" if not result.flagged_for_review else "⚠"
    grade_info = f"{result.letter_grade} ({result.percentage:.1f}%)" if result.letter_grade else "ERROR"
    print(f"  [{current}/{total}] {status} {student_name}: {grade_info}")


def run_grading_pipeline(
    assignment_name: str,
    dry_run: bool = False,
    batch_start: int = 0,
    batch_size: int = 20,
    delay_between_batches: float = 5.0
):
    """
    Run the complete grading pipeline.
    
    Args:
        assignment_name: Name of the assignment folder
        dry_run: If True, use mock responses (no API calls)
        batch_start: Index to start processing from (for resume)
        batch_size: Number of submissions per batch
        delay_between_batches: Seconds to wait between batches
    """
    # Load configuration
    project_root = Path(__file__).parent
    global_config = load_config(project_root / "config" / "settings.yaml")
    
    # Setup paths
    assignment_dir = project_root / "assignments" / assignment_name
    submissions_dir = assignment_dir / "submissions"
    rubric_path = assignment_dir / "rubric.png"
    output_dir = project_root / "output" / assignment_name
    
    # Validate paths
    if not assignment_dir.exists():
        print(f"✗ Assignment directory not found: {assignment_dir}")
        sys.exit(1)
    
    if not rubric_path.exists():
        print(f"✗ Rubric image not found: {rubric_path}")
        print("  Please add rubric.png to the assignment folder")
        sys.exit(1)
    
    if not submissions_dir.exists():
        print(f"✗ Submissions directory not found: {submissions_dir}")
        sys.exit(1)
    
    # Load assignment config if exists
    assignment_config_path = assignment_dir / "config.yaml"
    additional_instructions = None
    if assignment_config_path.exists():
        assignment_config = load_config(assignment_config_path)
        additional_instructions = assignment_config.get("instructions")
    
    # Setup output files
    grades_csv, flagged_csv, audit_log = setup_output_files(output_dir, assignment_name)
    
    # Initialize components
    print("\n" + "=" * 60)
    print("AI GRADER AGENT")
    print("=" * 60)
    print(f"\nAssignment: {assignment_name}")
    print(f"Mode: {'DRY RUN (no API calls)' if dry_run else 'LIVE'}")
    print(f"Model: {global_config['openai']['model']}")
    print(f"Batch size: {batch_size}")
    print(f"Confidence threshold: {global_config['grading']['confidence_threshold']}")
    
    # Process PDFs
    print("\n📄 Processing PDF submissions...")
    processor = PDFProcessor(submissions_dir)
    submissions = processor.get_all_submissions()
    summary = processor.get_submission_summary(submissions)
    
    print(f"   Found: {summary['total']} submissions")
    print(f"   Readable: {summary['successful']}")
    if summary['failed'] > 0:
        print(f"   ⚠ Failed to extract: {summary['failed']}")
        for name, reason in zip(summary['failed_names'], summary['failed_reasons']):
            print(f"      - {name}: {reason}")
    
    # Apply batch start offset
    submissions_to_process = submissions[batch_start:]
    if batch_start > 0:
        print(f"\n   Resuming from submission #{batch_start + 1}")
    
    # Initialize grader
    grader = GraderAgent(
        model=global_config['openai']['model'],
        max_tokens=global_config['openai']['max_tokens'],
        temperature=global_config['openai']['temperature'],
        confidence_threshold=global_config['grading']['confidence_threshold'],
        max_retries=global_config['grading']['max_retries']
    )
    
    # Test connection (skip in dry run)
    if not dry_run:
        print("\n🔌 Testing API connection...")
        if grader.test_connection():
            print("   ✓ Connected to OpenAI API")
        else:
            print("   ✗ Failed to connect to OpenAI API")
            print("   Check your OPENAI_API_KEY in .env file")
            sys.exit(1)
    
    # Grade submissions in batches
    print(f"\n📝 Grading {len(submissions_to_process)} submissions...\n")
    
    all_results: list[GradingResult] = []
    
    for batch_num, i in enumerate(range(0, len(submissions_to_process), batch_size)):
        batch = submissions_to_process[i:i + batch_size]
        batch_results = []
        
        if batch_num > 0:
            print(f"\n⏳ Waiting {delay_between_batches}s before next batch...")
            time.sleep(delay_between_batches)
        
        print(f"\n--- Batch {batch_num + 1} ({len(batch)} submissions) ---")
        
        for j, submission in enumerate(batch):
            result = grader.grade_submission(
                submission=submission,
                rubric_image_path=rubric_path,
                additional_instructions=additional_instructions,
                dry_run=dry_run
            )
            
            # Log and display progress
            current_num = batch_start + i + j + 1
            print_progress(current_num, len(submissions), submission.student_name, result)
            
            # Write to audit log immediately
            write_audit_log(result, audit_log)
            
            batch_results.append(result)
            
            # Small delay between submissions to avoid rate limits
            if not dry_run and j < len(batch) - 1:
                time.sleep(0.5)
        
        all_results.extend(batch_results)
    
    # Write output files
    print("\n" + "-" * 40)
    print("📊 Writing output files...")
    
    write_grades_csv(all_results, grades_csv)
    print(f"   ✓ Grades CSV: {grades_csv}")
    
    write_flagged_csv(all_results, flagged_csv)
    
    print(f"   ✓ Audit log: {audit_log}")
    
    # Summary
    successful = [r for r in all_results if not r.error]
    flagged = [r for r in all_results if r.flagged_for_review]
    errors = [r for r in all_results if r.error]
    
    print("\n" + "=" * 60)
    print("GRADING COMPLETE")
    print("=" * 60)
    print(f"\n   Total processed: {len(all_results)}")
    print(f"   Successful: {len(successful)}")
    print(f"   Flagged for review: {len(flagged)}")
    print(f"   Errors: {len(errors)}")
    
    if successful:
        avg_score = sum(r.percentage for r in successful) / len(successful)
        print(f"\n   Average score: {avg_score:.1f}%")
    
    print(f"\n📁 Output files saved to: {output_dir}")
    print("\nNext steps:")
    print("   1. Review flagged.csv for submissions needing human review")
    print("   2. Review grades.csv and make any needed adjustments")
    print("   3. Upload grades to Canvas manually")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Grader Agent - Grade student submissions using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --assignment assignment_1
  python main.py --assignment assignment_1 --dry-run
  python main.py --assignment assignment_1 --batch-start 20

Setup:
  1. Create .env file with OPENAI_API_KEY=your-key
  2. Place rubric.png in assignments/<name>/
  3. Place student PDFs in assignments/<name>/submissions/
  4. Run: python main.py --assignment <name>
        """
    )
    
    parser.add_argument(
        "--assignment", "-a",
        required=True,
        help="Name of the assignment folder (e.g., assignment_1)"
    )
    
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Run without API calls (uses mock responses)"
    )
    
    parser.add_argument(
        "--batch-start", "-b",
        type=int,
        default=0,
        help="Start from this submission index (for resume)"
    )
    
    parser.add_argument(
        "--batch-size", "-s",
        type=int,
        default=20,
        help="Number of submissions per batch (default: 20)"
    )
    
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Only test the API connection"
    )
    
    args = parser.parse_args()
    
    # Load env
    load_dotenv()
    
    if args.test_connection:
        print("Testing OpenAI API connection...")
        grader = GraderAgent()
        if grader.test_connection():
            print("✓ Connection successful!")
        else:
            print("✗ Connection failed")
            sys.exit(1)
        return
    
    # Run the pipeline
    run_grading_pipeline(
        assignment_name=args.assignment,
        dry_run=args.dry_run,
        batch_start=args.batch_start,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()