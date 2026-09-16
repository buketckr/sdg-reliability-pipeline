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

## Module Responsibilities

### `pipeline.py`

The main public entry point of the system.

It coordinates the complete evaluation workflow:

- Initial LLM evaluations
- Stage 1 reliability analysis
- Conditional Stage 2 re-evaluation
- Stage 3 final aggregation

---

### `llm_evaluator.py`

Handles all communication with the language model.

Responsibilities include:

- OpenAI API calls
- SDG evaluation prompt
- Repeated SDG1-SDG16 evaluations
- Response validation
- Retry handling

---

### `stage1.py`

Analyzes the five initial evaluations.

For each SDG, it determines whether the result is:

- `stable`
- `stable_near_boundary`
- `low_relevance_variation`
- `needs_additional_evaluation`

---

### `stage2.py`

Runs only when Stage 1 identifies one or more SDGs that require additional evaluation.

It:

- Performs three additional full SDG1-SDG16 evaluations
- Combines Stage 1 and Stage 2 results
- Reassesses category stability
- Produces reliability and uncertainty information

---

### `stage3.py`

Produces the final SDG1-SDG16 output.

It:

- Combines results resolved in Stage 1 with results resolved in Stage 2
- Selects the final score and category for each SDG
- Validates score/category consistency
- Produces the final result returned by the pipeline

---

### `config.py`

Stores shared configuration values used throughout the pipeline, including:

- Model name
- Temperature
- Number of initial runs
- Number of Stage 2 runs
- Category boundaries
- Near-boundary margin
- Reliability thresholds
- API retry settings

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

---

## Testing

A simple end-to-end test script is included to verify that the complete pipeline can run successfully.

```bash
python -m tests.test_pipeline
