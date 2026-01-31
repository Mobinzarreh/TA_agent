# AI Grader Agent

An AI-powered grading assistant that uses OpenAI's GPT to grade student PDF submissions against a rubric image, outputting grades and feedback to CSV.

## Features

- 📄 **PDF Processing**: Extracts text from student submission PDFs
- 🖼️ **Vision-Based Rubric**: Uses GPT's vision API to understand rubric images
- 📊 **Structured Output**: Generates consistent JSON with scores, feedback, and flags
- ⚠️ **Academic Integrity Detection**: Flags suspicious submissions for human review
- 🔄 **Batch Processing**: Handles large classes (120+ students) in batches of 20
- 🔁 **Resume Capability**: Can restart from any submission if interrupted
- 📝 **Audit Trail**: Complete logging of all grading decisions

## Quick Start

### 1. Prerequisites

- Python 3.12+
- OpenAI API key (GPT-4o-mini or GPT-4o)
- Poetry for dependency management

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/Mobinzarreh/TA_agent.git
cd TA_agent

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 3. Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-api-key-here
```

### 4. Setup Your Assignment

```bash
# Your rubric screenshot goes here
assignments/assignment_1/rubric.png

# Place student PDFs here (named as lastname.pdf)
assignments/assignment_1/submissions/smith.pdf
assignments/assignment_1/submissions/johnson.pdf
```

### 5. Run Grading

```bash
# Test with dry-run first (no API calls, uses mock data)
python main.py --assignment assignment_1 --dry-run

# Run actual grading
python main.py --assignment assignment_1

# Resume from a specific submission if interrupted
python main.py --assignment assignment_1 --batch-start 40
```

## Project Structure

```
grader_agent/
├── main.py                     # Entry point
├── config/
│   └── settings.yaml           # Global settings (model, batch size, etc.)
├── src/grader_agent/
│   ├── pdf_processor.py        # PDF text extraction
│   ├── prompt_builder.py       # Grading prompt templates
│   └── grader.py               # GPT grader agent
├── assignments/
│   └── assignment_1/
│       ├── rubric.png          # Rubric screenshot
│       ├── config.yaml         # Assignment-specific settings (optional)
│       └── submissions/        # Student PDFs (lastname.pdf)
└── output/
    └── assignment_1/
        ├── grades_YYYYMMDD_HHMMSS.csv      # Final grades
        ├── flagged_YYYYMMDD_HHMMSS.csv     # Flagged for review
        └── grading_log_YYYYMMDD_HHMMSS.jsonl  # Audit trail
```

## Output Files

### grades.csv
| Column | Description |
|--------|-------------|
| Student Name | From filename |
| Total Score | Points awarded |
| Max Score | Maximum possible |
| Percentage | Score percentage |
| Letter Grade | A through F |
| Feedback | Personalized feedback |
| Strengths | What student did well |
| Improvements | Areas to improve |
| Confidence | AI confidence (0-1) |

### flagged.csv
Submissions needing human review:
- Low confidence scores (< 0.7)
- Academic integrity concerns
- PDF extraction errors

## Configuration Options

### config/settings.yaml

```yaml
openai:
  model: "gpt-4o-mini"  # Vision-capable model
  max_tokens: 2000
  temperature: 0.3      # Lower = more consistent

batch:
  size: 20              # Submissions per batch
  delay_between_batches: 5  # Rate limiting

grading:
  confidence_threshold: 0.7  # Flag below this
  max_retries: 2
```

### Assignment config.yaml (optional)

```yaml
name: "Assignment 1"
instructions: |
  Additional grading instructions...
grade_scale:
  A: 90
  B: 80
  C: 70
  D: 60
  F: 0
max_score: 100
```

## Command Line Options

```
python main.py --help

Options:
  -a, --assignment    Assignment folder name (required)
  -d, --dry-run       Run without API calls (mock responses)
  -b, --batch-start   Start from this submission index
  -s, --batch-size    Submissions per batch (default: 20)
  --test-connection   Test API connection only
```

## Cost Estimate

Using GPT-4o-mini with single-agent design:

| Students | API Calls | Estimated Cost |
|----------|-----------|----------------|
| 20 | 20 | ~$0.40 |
| 60 | 60 | ~$1.20 |
| 120 | 120 | ~$2.40 |

## Workflow

1. **Prepare**: Place rubric.png and student PDFs in assignment folder
2. **Test**: Run with `--dry-run` to verify setup
3. **Grade**: Run actual grading
4. **Review**: Check flagged.csv for submissions needing human review
5. **Finalize**: Review grades.csv, make adjustments
6. **Upload**: Manually upload to Canvas

## Troubleshooting

### "No API key found"
- Ensure `.env` file exists in project root with `OPENAI_API_KEY=sk-...`
- Verify the key starts with `sk-proj-` or `sk-`

### "Rubric image not found"
- Add `rubric.png` to `assignments/assignment_1/` folder
- Supported formats: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`

### "No PDF files found"
- Add student PDFs to `assignments/assignment_1/submissions/`
- Ensure files are named `lastname.pdf` (e.g., `smith.pdf`)

### PDF extraction fails
- Some scanned PDFs may not extract text properly
- Flagged submissions show in `flagged.csv` for manual review
- Consider using OCR preprocessing for scanned documents

### API errors
- Check your OpenAI API key is valid and has credits
- Verify you're using a vision-capable model (`gpt-4o-mini` or `gpt-4o`)
- Reduce `batch_size` in `config/settings.yaml` if hitting rate limits

## Testing

Run with dry-run mode to test setup without API calls:

```bash
python main.py --assignment assignment_1 --dry-run
```

## License

MIT

## Author

Mobin Zarreh - mzarreh@asu.edu
