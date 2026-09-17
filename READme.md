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
- Token usage and LLM response-time aggregation
- Diagnostic output generation
---

### `llm_evaluator.py`

Handles all communication with the language model.

Responsibilities include:

- OpenAI API calls
- SDG evaluation prompt
- Repeated SDG1-SDG16 evaluations
- Response validation
- Retry handling
- Token usage collection and response-time measurement

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

`learningOutcomes` is optional. If it is not available, the course can be evaluated using the course description alone.

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
    },

    "token_usage": {
        "stage1": {
            "input_tokens": 4200,
            "output_tokens": 1080,
            "total_tokens": 5280
        },
        "stage2": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        },
        "overall": {
            "input_tokens": 4200,
            "output_tokens": 1080,
            "total_tokens": 5280
        }
    },

    "timing": {
        "stage1_seconds": 12.4,
        "stage2_seconds": 0.0,
        "overall_seconds": 12.4
    },

    "diagnostics": {
        "stage1_runs": [
            {
                "run": 1,
                "scores": {
                    "SDG1": 18,
                    "SDG2": 25
                },
                "response_time_seconds": 2.4,
                "input_tokens": 840,
                "output_tokens": 216,
                "total_tokens": 1056
            }
        ],

        "stage1_unresolved_pairs": [],
        "stage1_near_boundary_pairs": [],
        "stage2_runs": [],
        "stage2_results": []
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

### Pipeline Metadata

The `pipeline` field summarizes how the evaluation was performed:

- `initial_runs` — Number of initial LLM evaluations
- `stage2_performed` — Whether additional Stage 2 evaluation was required
- `stage2_extra_runs` — Number of additional Stage 2 runs

### Token Usage

The `token_usage` field reports token consumption for:

- Stage 1
- Stage 2
- The complete evaluation

Each section contains:

- `input_tokens`
- `output_tokens`
- `total_tokens`

If Stage 2 is not performed, its token values are zero.

### Timing

The `timing` field reports the accumulated LLM response time:

- `stage1_seconds`
- `stage2_seconds`
- `overall_seconds`

These values represent LLM API response time rather than complete application execution time.

### Diagnostics

The `diagnostics` field is provided mainly for development, testing, and troubleshooting.

It contains:

- Individual Stage 1 run scores
- Per-run token usage
- Per-run response time
- Stage 1 unresolved SDG pairs
- Stage 1 near-boundary pairs
- Individual Stage 2 runs, when Stage 2 is triggered
- Detailed Stage 2 results

The diagnostics section is not required to be displayed in the normal end-user interface.

---

## Recommended UI Presentation

The pipeline returns both SDG relevance results and reliability information.  
A frontend integrating this module should present the final SDG results in a way that keeps the relevance score and the reliability status distinguishable.

For each SDG, the UI should preferably display:

- SDG identifier
- Final correlation score
- Final category
- Reliability status


### Suggested Reliability Indicators

The UI may use short labels or badges for reliability-related statuses:

- `stable` — consistent category across the initial evaluations
- `stable_near_boundary` — consistent category, but the representative score is close to an important category boundary
- `low_relevance_variation` — variation exists only between lower-level adjacent categories
- `stable_after_recheck` — initially inconsistent result that became stable after Stage 2
- `unstable` — result remained unreliable after additional evaluation

The reliability status should not be presented as correctness or certainty about the true SDG relationship. It represents the repeatability and stability of the model output.

### Optional Detailed View

For users who need more information, the interface may provide an expandable details section containing:

- Category agreement
- Stage 1 scores
- Stage 2 scores, when applicable
- Whether the result was resolved in Stage 1 or Stage 2
- 95% confidence interval, when Stage 2 is performed
- Boundary sensitivity
- Reliability level, when available

Development or administrative interfaces may also use the returned diagnostic information to inspect individual LLM runs, token usage, and response times.

These details do not necessarily need to be shown in the default user interface.

---
## Testing

A simple end-to-end test script is included to verify that the complete pipeline can run successfully.

```bash
python -m tests.test_pipeline
