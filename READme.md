# SDG Reliability Evaluation Pipeline

This project provides a Python-based reliability evaluation pipeline for assessing the relationship between university courses and the United Nations Sustainable Development Goals (SDGs).

The system evaluates SDG1 through SDG16 based on a course description and its learning outcomes. SDG17 is not included.

The project is designed as a framework-independent Python module so that it can be integrated into an existing backend or frontend infrastructure.

---

## Overview

Large Language Model (LLM) evaluations may produce slightly different scores when the same course is evaluated multiple times.

To improve the repeatability of the final SDG classification, this project uses a multi-stage reliability evaluation process.

The complete pipeline is executed through a single function:

```python
from app.pipeline import run_pipeline

result = run_pipeline(course_data)

```

---

## Requirements

Python 3 is required.
Install project dependencies with:

```python
pip install -r requirements.txt

```

---

## Environment Configuration

Create a ```python .env ``` file in the project root.

An .env.example file is provided as a template.

---

## Input Format

The pipeline evaluates one course at a time.
The input must be a Python dictionary.


## Required Fields

```python
course_data = {
    "courseCode": "MGMT411",
    "courseDescEN": "Course description...",
    "learningOutcomes": [
        "Learning outcome 1",
        "Learning outcome 2",
        "Learning outcome 3"
    ]
}
```

learningOutcomes is not required.

---

## Output Format

 ```run_pipeline() ``` returns a standard Python dictionary.

 Example:
```python
{
    "course": "MGMT411",
    "evaluation": [
        {
            "SDGInfo": "SDG1",
            "correlation": 18,
            "category": "none/speculative",
            "status": "stable",
            "source": "stage1",
            "reliability": {
                "status": "stable",
                "category_agreement": 1.0,
                "dominant_category": "none/speculative",
                "category_counts": {
                    "none/speculative": 5
                },
                "boundary_flag": False,
                "boundary_between": None,
                "score_std": 2.0,
                "score_range": 4
            }
        }
    ],
    "summary": {
        "total_sdgs": 16
    },
    "pipeline": {
        "initial_runs": 5,
        "stage2_performed": False,
        "stage2_extra_runs": 0
    }
}

```


Each final SDG entry contains:

- `SDGInfo` — SDG identifier
- `correlation` — Final numeric score
- `category` — Final score category
- `status` — Reliability status
- `source` — Stage that produced the final result
- `reliability` — Additional reliability metadata








