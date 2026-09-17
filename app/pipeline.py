from app.config import (
    INITIAL_RUNS,
    STAGE2_RUNS,
)

from app.llm_evaluator import evaluate_course
from app.stage1 import run_stage1
from app.stage2 import run_stage2
from app.stage3 import run_stage3


# ============================================================
# TOKEN USAGE
# ============================================================

def summarize_token_usage(runs):
    """
    Sum token usage across multiple LLM runs.

    Expected run structure:

    {
        "run": 1,
        "evaluation": [...],
        "metadata": {
            "response_time_seconds": ...,
            "input_tokens": ...,
            "output_tokens": ...,
            "total_tokens": ...
        }
    }
    """

    token_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }

    if not runs:
        return token_usage

    for run in runs:

        metadata = run.get(
            "metadata",
            {},
        )

        token_usage[
            "input_tokens"
        ] += (
            metadata.get(
                "input_tokens"
            )
            or 0
        )

        token_usage[
            "output_tokens"
        ] += (
            metadata.get(
                "output_tokens"
            )
            or 0
        )

        token_usage[
            "total_tokens"
        ] += (
            metadata.get(
                "total_tokens"
            )
            or 0
        )

    return token_usage


# ============================================================
# RESPONSE TIME
# ============================================================

def summarize_response_time(runs):
    """
    Sum LLM response time across multiple runs.
    """

    total_seconds = 0.0

    if not runs:
        return total_seconds

    for run in runs:

        metadata = run.get(
            "metadata",
            {},
        )

        total_seconds += (
            metadata.get(
                "response_time_seconds"
            )
            or 0
        )

    return round(
        total_seconds,
        2,
    )


# ============================================================
# RUN DIAGNOSTICS
# ============================================================

def build_run_diagnostics(runs):
    """
    Build compact diagnostic information for each LLM run.

    Each run includes:
    - run number
    - SDG scores
    - response time
    - input tokens
    - output tokens
    - total tokens
    """

    diagnostics = []

    if not runs:
        return diagnostics

    for run in runs:

        evaluation = run.get(
            "evaluation",
            [],
        )

        scores = {
            item.get("SDGInfo"):
                item.get("correlation")
            for item in evaluation
        }

        metadata = run.get(
            "metadata",
            {},
        )

        diagnostics.append(
            {
                "run":
                    run.get("run"),

                "scores":
                    scores,

                "response_time_seconds":
                    (
                        metadata.get(
                            "response_time_seconds"
                        )
                        or 0
                    ),

                "input_tokens":
                    (
                        metadata.get(
                            "input_tokens"
                        )
                        or 0
                    ),

                "output_tokens":
                    (
                        metadata.get(
                            "output_tokens"
                        )
                        or 0
                    ),

                "total_tokens":
                    (
                        metadata.get(
                            "total_tokens"
                        )
                        or 0
                    ),
            }
        )

    return diagnostics


# ============================================================
# PIPELINE
# ============================================================

def run_pipeline(course_data):
    """
    Run the complete SDG reliability evaluation pipeline
    for a single course.

    Flow:
        1. Perform INITIAL_RUNS full SDG1-SDG16 evaluations.
        2. Calculate Stage 1 token usage, timing, and diagnostics.
        3. Run Stage 1 reliability analysis.
        4. If required, perform STAGE2_RUNS additional evaluations.
        5. Calculate Stage 2 token usage, timing, and diagnostics.
        6. Run Stage 3 final aggregation.
        7. Return final SDG results together with:
           - pipeline metadata
           - token usage
           - timing information
           - diagnostic information

    Parameters
    ----------
    course_data : dict
        Expected course structure:

        {
            "courseCode": "MGMT411",
            "courseDescEN": "Course description...",
            "learningOutcomes": [
                "Outcome 1",
                "Outcome 2"
            ]
        }

        The evaluator also supports "description"
        instead of "courseDescEN".

    Returns
    -------
    dict
        Complete SDG evaluation result.
    """

    if not isinstance(
        course_data,
        dict,
    ):
        raise ValueError(
            "course_data must be a dictionary."
        )

    # ========================================================
    # INITIAL EVALUATIONS
    # ========================================================

    initial_results = evaluate_course(
        course_data=course_data,
        num_runs=INITIAL_RUNS,
    )

    initial_runs = initial_results[
        "runs"
    ]

    # ========================================================
    # STAGE 1 TOKEN USAGE
    # ========================================================

    stage1_token_usage = (
        summarize_token_usage(
            initial_runs
        )
    )

    # ========================================================
    # STAGE 1 RESPONSE TIME
    # ========================================================

    stage1_response_time = (
        summarize_response_time(
            initial_runs
        )
    )

    # ========================================================
    # STAGE 1 DIAGNOSTICS
    # ========================================================

    stage1_diagnostics = (
        build_run_diagnostics(
            initial_runs
        )
    )

    # ========================================================
    # STAGE 1
    # ========================================================

    stage1_result = run_stage1(
        initial_results
    )

    # ========================================================
    # STAGE 2 DEFAULT VALUES
    # ========================================================

    stage2_result = None

    stage2_token_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }

    stage2_response_time = 0.0

    stage2_diagnostics = []

    # ========================================================
    # STAGE 2
    # ========================================================

    if stage1_result[
        "needs_stage2"
    ]:

        stage2_result = run_stage2(
            course_data=course_data,
            stage1_result=stage1_result,
        )

        stage2_runs = stage2_result.get(
            "raw_runs",
            [],
        )

        stage2_token_usage = (
            summarize_token_usage(
                stage2_runs
            )
        )

        stage2_response_time = (
            summarize_response_time(
                stage2_runs
            )
        )

        stage2_diagnostics = (
            build_run_diagnostics(
                stage2_runs
            )
        )

    # ========================================================
    # STAGE 3
    # ========================================================

    final_result = run_stage3(
        stage1_result=stage1_result,
        stage2_result=stage2_result,
    )

    # ========================================================
    # OVERALL TOKEN USAGE
    # ========================================================

    overall_token_usage = {
        "input_tokens":
            (
                stage1_token_usage[
                    "input_tokens"
                ]
                + stage2_token_usage[
                    "input_tokens"
                ]
            ),

        "output_tokens":
            (
                stage1_token_usage[
                    "output_tokens"
                ]
                + stage2_token_usage[
                    "output_tokens"
                ]
            ),

        "total_tokens":
            (
                stage1_token_usage[
                    "total_tokens"
                ]
                + stage2_token_usage[
                    "total_tokens"
                ]
            ),
    }

    # ========================================================
    # OVERALL RESPONSE TIME
    # ========================================================

    overall_response_time = round(
        stage1_response_time
        + stage2_response_time,
        2,
    )

    # ========================================================
    # PIPELINE METADATA
    # ========================================================

    final_result[
        "pipeline"
    ] = {
        "initial_runs":
            INITIAL_RUNS,

        "stage2_performed":
            stage2_result is not None,

        "stage2_extra_runs":
            (
                STAGE2_RUNS
                if stage2_result is not None
                else 0
            ),
    }

    # ========================================================
    # TOKEN USAGE
    # ========================================================

    final_result[
        "token_usage"
    ] = {
        "stage1":
            stage1_token_usage,

        "stage2":
            stage2_token_usage,

        "overall":
            overall_token_usage,
    }

    # ========================================================
    # TIMING
    # ========================================================

    final_result[
        "timing"
    ] = {
        "stage1_seconds":
            stage1_response_time,

        "stage2_seconds":
            stage2_response_time,

        "overall_seconds":
            overall_response_time,
    }

    # ========================================================
    # DIAGNOSTICS
    # ========================================================

    final_result[
        "diagnostics"
    ] = {
        "stage1_runs":
            stage1_diagnostics,

        "stage1_unresolved_pairs":
            stage1_result.get(
                "unresolved_pairs",
                [],
            ),

        "stage1_near_boundary_pairs":
            stage1_result.get(
                "near_boundary_pairs",
                [],
            ),

        "stage2_runs":
            stage2_diagnostics,

        "stage2_results":
            (
                stage2_result.get(
                    "results",
                    [],
                )
                if stage2_result is not None
                else []
            ),
    }

    return final_result