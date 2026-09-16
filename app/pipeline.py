from app.config import (
    INITIAL_RUNS,
    STAGE2_RUNS,
)

from app.llm_evaluator import evaluate_course
from app.stage1 import run_stage1
from app.stage2 import run_stage2
from app.stage3 import run_stage3

# ============================================================
# PIPELINE
# ============================================================

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
        5. Return the final result as a Python dictionary.

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
        Final SDG1-SDG16 evaluation result.
    """

    if not isinstance(course_data, dict):
        raise ValueError(
            "course_data must be a dictionary."
        )

    # --------------------------------------------------------
    # INITIAL LLM EVALUATIONS
    # --------------------------------------------------------

    initial_results = evaluate_course(
        course_data=course_data,
        num_runs=INITIAL_RUNS,
    )

    # --------------------------------------------------------
    # STAGE 1
    # --------------------------------------------------------

    stage1_result = run_stage1(
        initial_results
    )

    # --------------------------------------------------------
    # STAGE 2
    # --------------------------------------------------------

    stage2_result = None

    if stage1_result["needs_stage2"]:

        stage2_result = run_stage2(
            course_data=course_data,
            stage1_result=stage1_result,
        )

    # --------------------------------------------------------
    # STAGE 3
    # --------------------------------------------------------

    final_result = run_stage3(
        stage1_result=stage1_result,
        stage2_result=stage2_result,
    )

    # --------------------------------------------------------
    # OPTIONAL PIPELINE METADATA
    # --------------------------------------------------------

    final_result["pipeline"] = {
        "initial_runs": INITIAL_RUNS,
        "stage2_performed":
            stage2_result is not None,
        "stage2_extra_runs":
            STAGE2_RUNS
            if stage2_result is not None
            else 0,
    }

    return final_result