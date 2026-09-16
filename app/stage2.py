import math
import statistics
from collections import Counter

from scipy import stats

from app.llm_evaluator import evaluate_course
from app.stage1 import CATEGORY_ORDER, get_category


# ============================================================
# SETTINGS
# ============================================================

from app.config import (
    STAGE2_RUNS,
    MIN_COMBINED_CATEGORY_AGREEMENT,
    CATEGORY_ORDER,
    CATEGORY_BOUNDS,
)

from app.llm_evaluator import evaluate_course
from app.stage1 import get_category


# ============================================================
# CATEGORY HELPERS
# ============================================================

def get_category_bounds(category):
    try:
        return CATEGORY_BOUNDS[category]
    except KeyError:
        raise ValueError(
            f"Unknown category: {category}"
        )

def category_distance(category_a, category_b):
    """
    Calculate ordinal distance between two categories.

    Examples:
        moderate -> SDG-inclusive = 1
        indirect -> SDG-inclusive = 2
    """

    return abs(
        CATEGORY_ORDER.index(category_a)
        - CATEGORY_ORDER.index(category_b)
    )


def dominant_category(categories):
    """
    Return:
        dominant category,
        dominant count,
        agreement ratio

    If multiple categories are tied, the lower category is selected
    deterministically. The tie itself is checked separately when
    deciding stability.
    """

    if not categories:
        raise ValueError(
            "Cannot determine dominant category from an empty list."
        )

    counts = Counter(categories)

    max_count = max(
        counts.values()
    )

    tied = [
        category
        for category, count in counts.items()
        if count == max_count
    ]

    dominant = min(
        tied,
        key=CATEGORY_ORDER.index,
    )

    agreement = (
        max_count
        / len(categories)
    )

    return (
        dominant,
        int(max_count),
        float(agreement),
    )


def representative_score_for_category(
    scores,
    category,
):
    """
    Calculate the representative final score using only scores
    belonging to the selected final category.

    This prevents inconsistent combinations such as:

        score = 46
        category = indirect
    """

    matching_scores = [
        int(score)
        for score in scores
        if get_category(int(score)) == category
    ]

    if not matching_scores:
        return None

    return int(
        statistics.median(
            matching_scores
        )
    )


# ============================================================
# CONFIDENCE INTERVAL
# ============================================================

def calculate_confidence_interval(scores):
    """
    Calculate a 95% Student-t confidence interval for the mean
    score across repeated full-context evaluations.

    Important:
    This interval describes variation in repeated model scores.
    It does NOT represent the probability that the true SDG
    relevance lies inside the interval.
    """

    n = len(scores)

    if n == 0:
        raise ValueError(
            "Cannot calculate a confidence interval "
            "from an empty score list."
        )

    mean_score = float(
        statistics.mean(scores)
    )

    if n < 2:
        return {
            "n": n,
            "mean": mean_score,
            "std": None,
            "ci_lower": None,
            "ci_upper": None,
            "ci_half_width": None,
        }

    std = float(
        statistics.stdev(scores)
    )

    if std == 0:
        return {
            "n": n,
            "mean": mean_score,
            "std": 0.0,
            "ci_lower": mean_score,
            "ci_upper": mean_score,
            "ci_half_width": 0.0,
        }

    standard_error = (
        std
        / math.sqrt(n)
    )

    t_critical = float(
        stats.t.ppf(
            0.975,
            df=n - 1,
        )
    )

    margin = (
        t_critical
        * standard_error
    )

    return {
        "n": n,
        "mean": mean_score,
        "std": std,
        "ci_lower": mean_score - margin,
        "ci_upper": mean_score + margin,
        "ci_half_width": margin,
    }


# ============================================================
# EVALUATION HELPERS
# ============================================================

def evaluation_to_lookup(evaluation):
    """
    Convert an SDG evaluation list to:

        {
            "SDG1": 10,
            "SDG2": 20,
            ...
        }
    """

    if not isinstance(evaluation, list):
        raise ValueError(
            "Evaluation must be a list."
        )

    lookup = {}

    for item in evaluation:

        sdg = str(
            item["SDGInfo"]
        ).replace(
            " ",
            ""
        )

        score = int(
            item["correlation"]
        )

        lookup[sdg] = score

    return lookup


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_stage1_result(stage1_result):
    """
    Validate the object returned by run_stage1().
    """

    if not isinstance(stage1_result, dict):
        raise ValueError(
            "stage1_result must be a dictionary."
        )

    course_code = stage1_result.get(
        "course"
    )

    if not course_code:
        raise ValueError(
            "Stage 1 result does not contain a course code."
        )

    unresolved_pairs = stage1_result.get(
        "unresolved_pairs"
    )

    if not isinstance(
        unresolved_pairs,
        list,
    ):
        raise ValueError(
            "Stage 1 result does not contain "
            "a valid unresolved_pairs list."
        )

    return (
        course_code,
        unresolved_pairs,
    )


# ============================================================
# STAGE 2
# ============================================================

def run_stage2(
    course_data,
    stage1_result,
):
    """
    Perform Stage 2 targeted re-evaluation.

    Only course-SDG pairs marked as
    'needs_additional_evaluation' by Stage 1 are analyzed here.

    However, the LLM itself still performs three complete
    SDG1-SDG16 evaluations of the course so that Stage 2 uses
    the same full-context evaluation format as Stage 1.

    No files are read or written.
    """

    (
        course_code,
        unresolved_pairs,
    ) = validate_stage1_result(
        stage1_result
    )

    # --------------------------------------------------------
    # NOTHING TO RE-EVALUATE
    # --------------------------------------------------------

    if not unresolved_pairs:

        return {
            "course": course_code,
            "performed": False,
            "results": [],
            "raw_runs": [],
            "summary": {
                "problematic_pairs_evaluated": 0,
                "stable_after_recheck": 0,
                "unstable": 0,
            },
        }

    # --------------------------------------------------------
    # CHECK COURSE CONSISTENCY
    # --------------------------------------------------------

    input_course_code = course_data.get(
        "courseCode"
    )

    if input_course_code != course_code:
        raise ValueError(
            f"Course mismatch between course_data "
            f"({input_course_code}) and Stage 1 "
            f"({course_code})."
        )

    # --------------------------------------------------------
    # 3 NEW FULL SDG1-SDG16 EVALUATIONS
    # --------------------------------------------------------

    stage2_evaluations = evaluate_course(
        course_data=course_data,
        num_runs=STAGE2_RUNS,
    )

    raw_runs = stage2_evaluations[
        "runs"
    ]

    if len(raw_runs) != STAGE2_RUNS:
        raise ValueError(
            f"Stage 2 expected {STAGE2_RUNS} runs "
            f"but received {len(raw_runs)}."
        )

    stage2_run_lookups = [
        evaluation_to_lookup(
            run["evaluation"]
        )
        for run in raw_runs
    ]

    # --------------------------------------------------------
    # ANALYZE ONLY UNRESOLVED SDGs
    # --------------------------------------------------------

    results = []

    for stage1_item in unresolved_pairs:

        sdg = stage1_item[
            "sdg"
        ]

        stage1_scores = [
            int(score)
            for score in stage1_item[
                "stage1_scores"
            ]
        ]

        if len(stage1_scores) != 5:
            raise ValueError(
                f"{course_code} - {sdg} must contain "
                f"exactly 5 Stage 1 scores."
            )

        stage1_categories = [
            get_category(score)
            for score in stage1_scores
        ]

        # ----------------------------------------------------
        # STAGE 2 SCORES
        # ----------------------------------------------------

        stage2_scores = []

        for lookup in stage2_run_lookups:

            if sdg not in lookup:
                raise ValueError(
                    f"{sdg} is missing from a Stage 2 evaluation."
                )

            stage2_scores.append(
                int(
                    lookup[sdg]
                )
            )

        stage2_categories = [
            get_category(score)
            for score in stage2_scores
        ]

        # ----------------------------------------------------
        # COMBINE 5 + 3 = 8 OBSERVATIONS
        # ----------------------------------------------------

        combined_scores = (
            stage1_scores
            + stage2_scores
        )

        combined_categories = (
            stage1_categories
            + stage2_categories
        )

        # ----------------------------------------------------
        # CATEGORY SUMMARIES
        # ----------------------------------------------------

        (
            stage1_dominant,
            stage1_dominant_count,
            stage1_agreement,
        ) = dominant_category(
            stage1_categories
        )

        (
            stage2_dominant,
            stage2_dominant_count,
            stage2_agreement,
        ) = dominant_category(
            stage2_categories
        )

        (
            combined_dominant,
            combined_dominant_count,
            combined_agreement,
        ) = dominant_category(
            combined_categories
        )

        # ----------------------------------------------------
        # COMBINED TIE
        # ----------------------------------------------------

        combined_counts = Counter(
            combined_categories
        )

        combined_max_count = max(
            combined_counts.values()
        )

        combined_candidates = [
            category
            for category, count
            in combined_counts.items()
            if count == combined_max_count
        ]

        combined_tie = (
            len(combined_candidates) > 1
        )

        # ----------------------------------------------------
        # CROSS-STAGE CONSISTENCY
        # ----------------------------------------------------

        cross_stage_category_distance = (
            category_distance(
                stage1_dominant,
                stage2_dominant,
            )
        )

        stage2_supports_final_category = (
            stage2_dominant
            == combined_dominant
        )

        stage2_has_consensus = (
            stage2_dominant_count >= 2
        )

        no_severe_cross_stage_conflict = (
            cross_stage_category_distance < 2
        )

        enough_combined_agreement = (
            combined_agreement
            >= MIN_COMBINED_CATEGORY_AGREEMENT
        )

        # ----------------------------------------------------
        # FINAL CATEGORY
        # ----------------------------------------------------

        final_category = (
            combined_dominant
        )

        final_score = (
            representative_score_for_category(
                combined_scores,
                final_category,
            )
        )

        if final_score is None:
            raise ValueError(
                f"Could not calculate a representative "
                f"score for {course_code} - {sdg}."
            )

        # ----------------------------------------------------
        # STABILITY DECISION
        # ----------------------------------------------------

        stable_after_recheck = (
            enough_combined_agreement
            and stage2_has_consensus
            and stage2_supports_final_category
            and no_severe_cross_stage_conflict
            and not combined_tie
        )

        if stable_after_recheck:
            status = "stable_after_recheck"
        else:
            status = "unstable"

        # ----------------------------------------------------
        # CONFIDENCE INTERVAL
        # ----------------------------------------------------

        ci = calculate_confidence_interval(
            combined_scores
        )

        (
            category_lower,
            category_upper,
        ) = get_category_bounds(
            final_category
        )

        ci_inside_final_category = (
            ci["ci_lower"] >= category_lower
            and
            ci["ci_upper"] <= category_upper
        )

        boundary_sensitive = (
            not ci_inside_final_category
        )

        # ----------------------------------------------------
        # RELIABILITY LEVEL
        # ----------------------------------------------------

        if status == "unstable":

            reliability_level = "low"

        elif ci_inside_final_category:

            reliability_level = "high"

        else:

            reliability_level = "medium"

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        result = {
            "course":
                course_code,

            "sdg":
                sdg,

            # Stage 1
            "stage1_scores":
                stage1_scores,

            "stage1_categories":
                stage1_categories,

            "stage1_dominant_category":
                stage1_dominant,

            "stage1_dominant_count":
                stage1_dominant_count,

            "stage1_category_agreement":
                stage1_agreement,

            # Stage 2
            "stage2_scores":
                stage2_scores,

            "stage2_categories":
                stage2_categories,

            "stage2_dominant_category":
                stage2_dominant,

            "stage2_dominant_count":
                stage2_dominant_count,

            "stage2_category_agreement":
                stage2_agreement,

            # Combined
            "combined_scores":
                combined_scores,

            "combined_categories":
                combined_categories,

            "combined_dominant_category":
                combined_dominant,

            "combined_dominant_count":
                combined_dominant_count,

            "combined_category_agreement":
                combined_agreement,

            "combined_candidates":
                combined_candidates,

            "combined_tie":
                combined_tie,

            # Cross-stage checks
            "stage2_supports_final_category":
                stage2_supports_final_category,

            "stage2_has_consensus":
                stage2_has_consensus,

            "cross_stage_category_distance":
                cross_stage_category_distance,

            "no_severe_cross_stage_conflict":
                no_severe_cross_stage_conflict,

            # CI / uncertainty
            "mean_score":
                float(ci["mean"]),

            "std":
                (
                    float(ci["std"])
                    if ci["std"] is not None
                    else None
                ),

            "ci_95_lower":
                (
                    float(ci["ci_lower"])
                    if ci["ci_lower"] is not None
                    else None
                ),

            "ci_95_upper":
                (
                    float(ci["ci_upper"])
                    if ci["ci_upper"] is not None
                    else None
                ),

            "ci_half_width":
                (
                    float(ci["ci_half_width"])
                    if ci["ci_half_width"] is not None
                    else None
                ),

            "ci_inside_final_category":
                ci_inside_final_category,

            "boundary_sensitive":
                boundary_sensitive,

            # Final Stage 2 decision
            "status":
                status,

            "reliability_level":
                reliability_level,

            "final_category":
                final_category,

            "final_score":
                final_score,
        }

        results.append(
            result
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    stable_after_recheck_count = sum(
        1
        for item in results
        if item["status"]
        == "stable_after_recheck"
    )

    unstable_count = sum(
        1
        for item in results
        if item["status"]
        == "unstable"
    )

    return {
        "course":
            course_code,

        "performed":
            True,

        "results":
            results,

        "raw_runs":
            raw_runs,

        "summary": {
            "problematic_pairs_evaluated":
                len(results),

            "stable_after_recheck":
                stable_after_recheck_count,

            "unstable":
                unstable_count,
        },
    }