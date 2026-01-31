# Setup Instructions

## 📋 How to Use This Grader

### Step 1: Add Your Rubric
1. Take a screenshot of your assignment rubric
2. Save it as `rubric.png` in this folder
3. Or use a different name and update `config.yaml`

### Step 2: Add Student Submissions
1. Collect all student PDF submissions
2. Rename them to `lastname.pdf` format:
   - `smith.pdf`
   - `johnson.pdf`
   - `garcia.pdf`
3. Place them in the `submissions/` folder

### Step 3: Customize Grading (Optional)
Edit `config.yaml` to:
- Add specific grading instructions
- Adjust grade scale (A/B/C/D/F thresholds)
- Set maximum score

### Step 4: Run Grading
From the project root:
```bash
# Dry run first (no API calls)
python main.py --assignment assignment_1 --dry-run

# Actual grading
python main.py --assignment assignment_1
```

### Step 5: Review Results
Check the `output/assignment_1/` folder for:
- `grades_*.csv` - All grades and feedback
- `flagged_*.csv` - Submissions needing human review

---

## 📁 Expected Folder Structure

```
assignment_1/
├── config.yaml           # Assignment settings
├── rubric.png            # Your rubric screenshot (ADD THIS)
├── submissions/          # Student PDFs (ADD THESE)
│   ├── smith.pdf
│   ├── johnson.pdf
│   └── ...
└── README.md            # This file
```
