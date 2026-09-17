from app.config import (
    INITIAL_RUNS,
    STAGE2_RUNS,
)

from app.llm_evaluator import evaluate_course
from app.stage1 import run_stage1
from app.stage2 import run_stage2
from app.stage3 import run_stage3


def summarize_token_usage(runs):
    """
    Sum token usage across multiple LLM runs.

    Expected run structure:

    {
        "run": 1,
        "evaluation": [...],
        "metadata": {
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


def run_pipeline(course_data):
    """
    Run the complete SDG reliability evaluation pipeline
    for a single course.

    Flow:
        1. Perform 5 initial full SDG1-SDG16 evaluations.
        2. Run Stage 1 reliability analysis.
        3. If necessary, perform 3 additional full evaluations
           and run Stage 2 analysis.
        4. Run Stage 3 final aggregation.
        5. Calculate token usage for Stage 1, Stage 2,
           and the complete pipeline.
        6. Return the final result as a Python dictionary.

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

        The evaluator also supports "description" instead of
        "courseDescEN".

    Returns
    -------
    dict
        Final SDG1-SDG16 evaluation result,
        including pipeline metadata and token usage.
    """

    if not isinstance(
        course_data,
        dict,
    ):
        raise ValueError(
            "course_data must be a dictionary."
        )


    initial_results = evaluate_course(
        course_data=course_data,
        num_runs=INITIAL_RUNS,
    )


    stage1_token_usage = (
        summarize_token_usage(
            initial_results[
                "runs"
            ]
        )
    )


    stage1_result = run_stage1(
        initial_results
    )

    stage2_result = None

    stage2_token_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }

    if stage1_result[
        "needs_stage2"
    ]:

        stage2_result = run_stage2(
            course_data=course_data,
            stage1_result=stage1_result,
        )

        # Stage 2 stores the additional LLM evaluations
        # under raw_runs.
        stage2_token_usage = (
            summarize_token_usage(
                stage2_result[
                    "raw_runs"
                ]
            )
        )


    final_result = run_stage3(
        stage1_result=stage1_result,
        stage2_result=stage2_result,
    )


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

    return final_result