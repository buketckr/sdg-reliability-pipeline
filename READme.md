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
                "reliability_level":"high",
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
- Reliability level


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
```

---

## Evaluation Flow and Terminology

This section explains how the evaluation pipeline works and how the main reliability-related terms are produced.

### 1. Course Input

The pipeline receives one course at a time as a Python dictionary.

The same course information is used for every repeated evaluation in the pipeline.

### 2. Initial LLM Evaluations

Stage 1 starts by evaluating the same course five independent times.

Each LLM call evaluates SDG1 through SDG16 and returns a numeric correlation score between 0 and 100 for every SDG.

Example:

```text
Run 1 -> SDG8 = 72
Run 2 -> SDG8 = 74
Run 3 -> SDG8 = 72
Run 4 -> SDG8 = 71
Run 5 -> SDG8 = 73
```

These repeated evaluations are used to measure output repeatability.

### 3. Score Categories

Every numeric score is mapped to one of five predefined categories.

| Score Range | Category |
|---|---|
| 0-19 | `none/speculative` |
| 20-39 | `indirect` |
| 40-69 | `moderate` |
| 70-89 | `SDG-inclusive` |
| 90-100 | `SDG-focused` |

The reliability analysis primarily compares categories rather than requiring the numeric scores to be identical.

---

## Stage 1 Reliability Analysis

Stage 1 analyzes the five initial scores separately for each SDG.

### `scores`

The five numeric scores returned by the initial LLM evaluations.

```python
"scores": [72, 72, 72, 58, 62]
```

### `categories`

The category corresponding to each numeric score.

```python
"categories": [
    "SDG-inclusive",
    "SDG-inclusive",
    "SDG-inclusive",
    "moderate",
    "moderate"
]
```

### `category_counts`

The number of times each category occurred.

```python
"category_counts": {
    "moderate": 2,
    "SDG-inclusive": 3
}
```

### `dominant_category`

The category that appears most frequently across the repeated evaluations.

### `category_agreement`

The proportion of runs belonging to the dominant category.

```text
dominant category count / number of runs
```

For example:

```text
3 / 5 = 0.60
```

A value of `1.0` means all five runs produced the same category.

### `representative_score`

The representative Stage 1 score is the median of the five scores.

### `representative_category`

The category corresponding to the representative score.

### `stable`

A result is marked as `stable` when all five initial evaluations belong to the same category and the representative score is not close to one of the important higher-level category boundaries.

### `stable_near_boundary`

A result is marked as `stable_near_boundary` when all five evaluations belong to the same category, but the representative score is close to one of the important category boundaries.

The pipeline currently monitors the boundaries between:

```text
moderate <-> SDG-inclusive
SDG-inclusive <-> SDG-focused
```

### `low_relevance_variation`

Some category changes are treated as lower-impact variation and do not trigger Stage 2.

These are variations limited to:

```text
none/speculative <-> indirect
```

or:

```text
indirect <-> moderate
```

### `needs_additional_evaluation`

An SDG is marked as `needs_additional_evaluation` when the five initial evaluations contain a more meaningful category disagreement.

For example:

```text
72, 72, 72, 58, 62
```

produces both `SDG-inclusive` and `moderate` classifications, so the SDG is sent to Stage 2.

### Stage 1 reliability-level mapping

- `stable` -> `high`
- `stable_near_boundary` -> `medium`
- `low_relevance_variation` -> `medium`

---

## Stage 2 Re-evaluation

Stage 2 runs only when at least one SDG receives `needs_additional_evaluation` during Stage 1.

Three additional full SDG1-SDG16 LLM evaluations are performed.

```text
5 Stage 1 evaluations
+
3 Stage 2 evaluations
=
8 total observations
```

Although the complete course is evaluated again, Stage 2 reliability analysis is applied only to the SDGs that were unresolved in Stage 1.

### `stage2_dominant_category`

The most frequent category among the three new Stage 2 evaluations.

### `stage2_has_consensus`

Stage 2 requires at least two of the three new evaluations to support the same dominant category.

### `combined_scores`

The five Stage 1 scores and three Stage 2 scores are combined.

### `combined_dominant_category`

The most frequent category across all eight observations.

### `combined_category_agreement`

The proportion of all eight evaluations that belong to the combined dominant category.

```text
combined dominant count / 8
```

The current pipeline requires at least `0.75` combined category agreement for a result to be considered stable after re-evaluation.

### `combined_tie`

A combined tie occurs when two or more categories have the same highest frequency across the eight evaluations.

A tied result is not treated as stable.

### `cross_stage_category_distance`

The system compares the Stage 1 dominant category with the Stage 2 dominant category using this ordered scale:

```text
none/speculative
indirect
moderate
SDG-inclusive
SDG-focused
```

The distance represents how many category levels separate the two dominant categories.

### `stage2_supports_final_category`

This value indicates whether the Stage 2 dominant category agrees with the combined final dominant category.

### `stable_after_recheck`

An unresolved Stage 1 result becomes `stable_after_recheck` only when all Stage 2 safeguards are satisfied:

- Combined category agreement is at least `0.75`
- Stage 2 has at least a 2/3 category consensus
- Stage 2 dominant category matches the combined dominant category
- No severe cross-stage category conflict exists
- No combined category tie exists

### `unstable`

If one or more Stage 2 stability checks fail, the result is marked as:

```python
"status": "unstable"
```

This means that repeated model evaluations did not provide sufficient category stability.

It does not mean that the SDG relationship is objectively incorrect.

---

## Final Stage 2 Score

After the final category is selected, the final numeric score is calculated using the median of only the scores that belong to that final category.

Example:

```text
Combined scores:
72, 72, 72, 58, 62, 58, 72, 72

Final category:
SDG-inclusive
```

Only scores belonging to `SDG-inclusive` are used:

```text
72, 72, 72, 72, 72
```

Final score:

```text
72
```

---

## Confidence Interval

For SDGs processed through Stage 2, the pipeline calculates a 95% Student-t confidence interval using all eight numeric scores.

The confidence interval is used as a descriptive measure of repeated-score variation.

### `ci_inside_final_category`

This field indicates whether the entire 95% confidence interval remains inside the numeric range of the final category.

### `boundary_sensitive`

A Stage 2 result is considered boundary-sensitive when the confidence interval crosses the numeric boundary of the final category.

---

## Reliability Level

Each final SDG result includes a reliability level.

The reliability level describes the repeatability and stability of the model output. It should not be interpreted as a probability that the SDG classification is objectively correct.

### Stage 1 Reliability Levels

For results resolved in Stage 1:

- `stable` -> `high`
- `stable_near_boundary` -> `medium`
- `low_relevance_variation` -> `medium`

A result marked as `needs_additional_evaluation` does not receive a final Stage 1 reliability level because it proceeds to Stage 2.

### Stage 2 Reliability Levels

For results processed through Stage 2:

#### `high`

The result passes all Stage 2 stability checks and its 95% confidence interval remains entirely within the final category.

#### `medium`

The result passes the Stage 2 stability checks, but the confidence interval crosses a category boundary.

#### `low`

The result remains `unstable` after Stage 2.

---

## Stage 3 Final Aggregation

Stage 3 creates the final SDG1-SDG16 result returned by the pipeline.

For each SDG:

- Results resolved in Stage 1 use the Stage 1 representative score and category.
- Results requiring Stage 2 use the Stage 2 final score and category.

The final result records whether the result came from:

```python
"source": "stage1"
```

or:

```python
"source": "stage2"
```

Stage 3 also validates that the final numeric score belongs to the reported category.

---

