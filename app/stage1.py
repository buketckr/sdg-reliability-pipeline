import re
from collections import Counter
from statistics import mean, median, stdev


# ============================================================
# SETTINGS
# ============================================================

from app.config import (
    INITIAL_RUNS,
    BOUNDARY_MARGIN,
    CATEGORY_ORDER,
)


# ============================================================
# CATEGORY HELPERS
# ============================================================

def normalize_sdg(value):
    """
    Normalize SDG labels such as 'SDG 8' or 'sdg8' to 'SDG8'.
    """

    match = re.search(
        r"SDG\s*(\d+)",
        str(value),
        re.IGNORECASE,
    )

    if match:
        return f"SDG{int(match.group(1))}"

    return str(value).strip()


def get_category(score):
    """
    Convert a numeric SDG correlation score to its category.
    """

    if score <= 19:
        return "none/speculative"

    if score <= 39:
        return "indirect"

    if score <= 69:
        return "moderate"

    if score <= 89:
        return "SDG-inclusive"

    return "SDG-focused"


def get_category_counts(categories):
    """
    Count category occurrences while preserving category order.
    """

    counts = Counter(categories)

    return {
        category: counts[category]
        for category in CATEGORY_ORDER
        if counts[category] > 0
    }


def get_dominant_category(categories):
    """
    Return the most frequent category and its count.

    If a tie occurs, the lower category is selected deterministically.
    With five Stage 1 runs, a complete top-frequency tie is uncommon,
    but the rule is retained for robustness.
    """

    counts = get_category_counts(categories)

    max_count = max(counts.values())

    tied_categories = [
        category
        for category, count in counts.items()
        if count == max_count
    ]

    dominant_category = min(
        tied_categories,
        key=CATEGORY_ORDER.index,
    )

    return dominant_category, max_count


# ============================================================
# BOUNDARY HELPERS
# ============================================================

def get_boundary_info(score):
    """
    Detect whether the representative score is close to one
    of the two important higher-level category boundaries.

    Important boundaries:
        69 / 70 -> moderate / SDG-inclusive
        89 / 90 -> SDG-inclusive / SDG-focused

    With margin = 3:
        66-73
        86-93
    """

    if (
        69 - BOUNDARY_MARGIN
        <= score
        <= 70 + BOUNDARY_MARGIN
    ):
        return (
            True,
            "moderate / SDG-inclusive",
        )

    if (
        89 - BOUNDARY_MARGIN
        <= score
        <= 90 + BOUNDARY_MARGIN
    ):
        return (
            True,
            "SDG-inclusive / SDG-focused",
        )

    return False, None


def is_noncritical_low_variation(unique_categories):
    """
    Determine whether observed category variation is considered
    low-level and does not require Stage 2.

    Current policy:
        none/speculative <-> indirect
        indirect <-> moderate

    These rules can be adjusted later without changing the rest
    of the Stage 1 pipeline.
    """

    if unique_categories.issubset(
        {
            "none/speculative",
            "indirect",
        }
    ):
        return True

    if unique_categories.issubset(
        {
            "indirect",
            "moderate",
        }
    ):
        return True

    return False


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_initial_results(initial_results):
    """
    Validate the object returned by llm_evaluator.evaluate_course().

    Expected shape:

    {
        "course": "MGMT411",
        "runs": [
            {
                "run": 1,
                "evaluation": [...]
            },
            ...
        ]
    }
    """

    if not isinstance(initial_results, dict):
        raise ValueError(
            "Stage 1 input must be a dictionary."
        )

    course_code = initial_results.get("course")

    if not course_code:
        raise ValueError(
            "Stage 1 input does not contain a course code."
        )

    runs = initial_results.get("runs")

    if not isinstance(runs, list):
        raise ValueError(
            "Stage 1 input does not contain a valid 'runs' list."
        )

    if len(runs) != INITIAL_RUNS:
        raise ValueError(
            f"Stage 1 expects exactly {INITIAL_RUNS} initial runs, "
            f"but received {len(runs)}."
        )

    expected_sdgs = [
        f"SDG{i}"
        for i in range(1, 17)
    ]

    for expected_run_number, run in enumerate(
        runs,
        start=1,
    ):
        if not isinstance(run, dict):
            raise ValueError(
                f"Run {expected_run_number} is invalid."
            )

        evaluation = run.get("evaluation")

        if not isinstance(evaluation, list):
            raise ValueError(
                f"Run {expected_run_number} does not contain "
                f"a valid evaluation list."
            )

        if len(evaluation) != 16:
            raise ValueError(
                f"Run {expected_run_number} contains "
                f"{len(evaluation)} SDGs instead of 16."
            )

        received_sdgs = [
            normalize_sdg(item.get("SDGInfo"))
            for item in evaluation
        ]

        if received_sdgs != expected_sdgs:
            raise ValueError(
                f"Run {expected_run_number} does not contain "
                f"SDG1-SDG16 in the expected order."
            )

    return course_code, runs


# ============================================================
# STAGE 1
# ============================================================

def run_stage1(initial_results):
    """
    Perform Stage 1 reliability analysis.

    Stage 1 logic:

    1. Use five independent initial evaluations.
    2. Compare the five categories for each SDG.
    3. If all five categories agree:
         - stable
         - or stable_near_boundary
    4. If category variation is low-level:
         - low_relevance_variation
    5. Otherwise:
         - needs_additional_evaluation
         - send that SDG to Stage 2

    Returns all Stage 1 results in memory.
    No files are read or written.
    """

    course_code, runs = validate_initial_results(
        initial_results
    )

    # --------------------------------------------------------
    # Collect scores for SDG1-SDG16
    # --------------------------------------------------------

    sdg_scores = {
        f"SDG{i}": []
        for i in range(1, 17)
    }

    for run in runs:

        evaluation = run["evaluation"]

        for item in evaluation:

            sdg = normalize_sdg(
                item["SDGInfo"]
            )

            score = int(
                item["correlation"]
            )

            sdg_scores[sdg].append(score)

    # --------------------------------------------------------
    # Analyze each course-SDG pair
    # --------------------------------------------------------

    results = []
    unresolved_pairs = []
    near_boundary_pairs = []

    for sdg_number in range(1, 17):

        sdg = f"SDG{sdg_number}"

        scores = sdg_scores[sdg]

        if len(scores) != INITIAL_RUNS:
            raise ValueError(
                f"{course_code} - {sdg} contains "
                f"{len(scores)} scores instead of {INITIAL_RUNS}."
            )

        categories = [
            get_category(score)
            for score in scores
        ]

        unique_categories = set(categories)

        category_counts = get_category_counts(
            categories
        )

        (
            dominant_category,
            dominant_count,
        ) = get_dominant_category(
            categories
        )

        mean_score = float(
            mean(scores)
        )

        median_score = int(
            median(scores)
        )

        score_std = float(
            stdev(scores)
        )

        score_range = int(
            max(scores) - min(scores)
        )

        representative_score = median_score

        representative_category = get_category(
            representative_score
        )

        category_agreement = (
            dominant_count
            / INITIAL_RUNS
        )

        boundary_flag = False
        boundary_between = None

        # ----------------------------------------------------
        # STATUS DECISION
        # ----------------------------------------------------

        if len(unique_categories) == 1:

            (
                boundary_flag,
                boundary_between,
            ) = get_boundary_info(
                representative_score
            )

            if boundary_flag:
                status = "stable_near_boundary"
            else:
                status = "stable"

        elif is_noncritical_low_variation(
            unique_categories
        ):
            status = "low_relevance_variation"

        else:
            status = "needs_additional_evaluation"

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        result = {
            "course": course_code,
            "sdg": sdg,

            "scores": scores,
            "categories": categories,

            "category_counts": category_counts,

            "dominant_category":
                dominant_category,

            "dominant_count":
                dominant_count,

            "category_agreement":
                category_agreement,

            "representative_score":
                representative_score,

            "representative_category":
                representative_category,

            "mean_score":
                mean_score,

            "median_score":
                median_score,

            "score_std":
                score_std,

            "score_range":
                score_range,

            "boundary_flag":
                boundary_flag,

            "boundary_between":
                boundary_between,

            "status":
                status,
        }

        results.append(result)

        # ----------------------------------------------------
        # STAGE 2 INPUT
        # ----------------------------------------------------

        if status == "needs_additional_evaluation":

            unresolved_pairs.append(
                {
                    "course":
                        course_code,

                    "sdg":
                        sdg,

                    "stage1_scores":
                        scores,

                    "stage1_categories":
                        categories,

                    "stage1_dominant_category":
                        dominant_category,

                    "stage1_dominant_count":
                        dominant_count,

                    "stage1_category_agreement":
                        category_agreement,

                    "stage1_representative_score":
                        representative_score,

                    "stage1_representative_category":
                        representative_category,
                }
            )

        # ----------------------------------------------------
        # NEAR-BOUNDARY INFORMATION
        # ----------------------------------------------------

        if status == "stable_near_boundary":

            near_boundary_pairs.append(
                {
                    "course":
                        course_code,

                    "sdg":
                        sdg,

                    "scores":
                        scores,

                    "category":
                        representative_category,

                    "representative_score":
                        representative_score,

                    "boundary_between":
                        boundary_between,
                }
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    status_counts = Counter(
        result["status"]
        for result in results
    )

    summary = {
        "total_pairs": len(results),

        "stable":
            status_counts.get(
                "stable",
                0,
            ),

        "stable_near_boundary":
            status_counts.get(
                "stable_near_boundary",
                0,
            ),

        "low_relevance_variation":
            status_counts.get(
                "low_relevance_variation",
                0,
            ),

        "needs_additional_evaluation":
            status_counts.get(
                "needs_additional_evaluation",
                0,
            ),
    }

    stable_total = (
        summary["stable"]
        + summary["stable_near_boundary"]
    )

    summary["stable_percent"] = (
        stable_total
        / len(results)
        * 100
    )

    # ========================================================
    # FINAL STAGE 1 OBJECT
    # ========================================================

    return {
        "course": course_code,

        "results": results,

        "unresolved_pairs":
            unresolved_pairs,

        "near_boundary_pairs":
            near_boundary_pairs,

        "needs_stage2":
            len(unresolved_pairs) > 0,

        "summary":
            summary,
    }