from collections import Counter

from app.stage1 import get_category


# ============================================================
# HELPERS
# ============================================================

def sdg_number(value):
    """
    Convert an SDG label such as 'SDG8' to integer 8.
    """

    return int(
        str(value)
        .replace("SDG", "")
        .strip()
    )


def build_stage2_lookup(stage2_result):
    """
    Convert Stage 2 results into a lookup:

        {
            "SDG8": {...},
            "SDG9": {...}
        }

    Returns an empty dictionary if Stage 2 was not performed.
    """

    if not stage2_result:
        return {}

    results = stage2_result.get(
        "results",
        []
    )

    if not isinstance(results, list):
        raise ValueError(
            "Stage 2 result does not contain "
            "a valid 'results' list."
        )

    return {
        item["sdg"]: item
        for item in results
    }


# ============================================================
# STAGE 1 RELIABILITY METADATA
# ============================================================

def build_stage1_reliability(stage1_item):
    """
    Build reliability metadata for a result resolved in Stage 1.

    Stage 1 does not assign formal high / medium / low
    reliability levels.

    Instead, its reliability information is based on:
        - category agreement
        - category counts
        - boundary information
        - score variation
    """

    return {
        "status":
            stage1_item["status"],

        "category_agreement":
            float(
                stage1_item[
                    "category_agreement"
                ]
            ),

        "dominant_category":
            stage1_item[
                "dominant_category"
            ],

        "category_counts":
            stage1_item[
                "category_counts"
            ],

        "boundary_flag":
            bool(
                stage1_item[
                    "boundary_flag"
                ]
            ),

        "boundary_between":
            stage1_item[
                "boundary_between"
            ],

        "score_std":
            float(
                stage1_item[
                    "score_std"
                ]
            ),

        "score_range":
            int(
                stage1_item[
                    "score_range"
                ]
            ),
    }


# ============================================================
# STAGE 2 RELIABILITY METADATA
# ============================================================

def build_stage2_reliability(stage2_item):
    """
    Build reliability metadata for a pair that reached Stage 2.
    """

    return {
        "status":
            stage2_item["status"],

        "combined_category_agreement":
            float(
                stage2_item[
                    "combined_category_agreement"
                ]
            ),

        "ci_95_lower":
            stage2_item.get(
                "ci_95_lower"
            ),

        "ci_95_upper":
            stage2_item.get(
                "ci_95_upper"
            ),

        "ci_half_width":
            stage2_item.get(
                "ci_half_width"
            ),

        "ci_inside_final_category":
            bool(
                stage2_item.get(
                    "ci_inside_final_category",
                    False,
                )
            ),

        "boundary_sensitive":
            bool(
                stage2_item.get(
                    "boundary_sensitive",
                    False,
                )
            ),

        "reliability_level":
            stage2_item.get(
                "reliability_level"
            ),

        "stage2_supports_final_category":
            bool(
                stage2_item.get(
                    "stage2_supports_final_category",
                    False,
                )
            ),

        "stage2_has_consensus":
            bool(
                stage2_item.get(
                    "stage2_has_consensus",
                    False,
                )
            ),

        "stage1_dominant_category":
            stage2_item.get(
                "stage1_dominant_category"
            ),

        "stage2_dominant_category":
            stage2_item.get(
                "stage2_dominant_category"
            ),

        "cross_stage_category_distance":
            int(
                stage2_item.get(
                    "cross_stage_category_distance",
                    0,
                )
            ),

        "combined_tie":
            bool(
                stage2_item.get(
                    "combined_tie",
                    False,
                )
            ),

        "no_severe_cross_stage_conflict":
            bool(
                stage2_item.get(
                    "no_severe_cross_stage_conflict",
                    True,
                )
            ),

        "stage1_scores":
            stage2_item.get(
                "stage1_scores",
                [],
            ),

        "stage2_scores":
            stage2_item.get(
                "stage2_scores",
                [],
            ),
    }


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_stage1_result(stage1_result):
    """
    Validate the result returned by run_stage1().
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

    results = stage1_result.get(
        "results"
    )

    if not isinstance(results, list):
        raise ValueError(
            "Stage 1 result does not contain "
            "a valid results list."
        )

    if len(results) != 16:
        raise ValueError(
            f"Stage 3 expects 16 Stage 1 SDG results, "
            f"but received {len(results)}."
        )

    return (
        course_code,
        results,
    )


# ============================================================
# FINAL CONSISTENCY CHECK
# ============================================================

def validate_final_score_category(
    course_code,
    sdg,
    score,
    category,
):
    """
    Ensure that the final numeric score belongs to the
    reported final category.
    """

    calculated_category = get_category(
        score
    )

    if calculated_category != category:

        raise ValueError(
            f"Inconsistent final result for "
            f"{course_code} - {sdg}: "
            f"score {score} maps to "
            f"'{calculated_category}', "
            f"but final category is "
            f"'{category}'."
        )


# ============================================================
# STAGE 3
# ============================================================

def run_stage3(
    stage1_result,
    stage2_result=None,
):
    """
    Perform final aggregation.

    For each SDG:

    - If Stage 1 resolved the pair:
        use the Stage 1 representative score/category.

    - If Stage 1 marked the pair as
      needs_additional_evaluation:
        use the corresponding Stage 2 final result.

    The final score/category consistency is validated before
    returning the result.

    No files are read or written.
    """

    (
        course_code,
        stage1_results,
    ) = validate_stage1_result(
        stage1_result
    )

    # --------------------------------------------------------
    # STAGE 2 LOOKUP
    # --------------------------------------------------------

    stage2_lookup = build_stage2_lookup(
        stage2_result
    )

    final_evaluations = []

    # --------------------------------------------------------
    # BUILD FINAL RESULT FOR SDG1-SDG16
    # --------------------------------------------------------

    for stage1_item in stage1_results:

        sdg = stage1_item[
            "sdg"
        ]

        stage1_status = stage1_item[
            "status"
        ]

        # ====================================================
        # CASE 1:
        # PAIR REQUIRED STAGE 2
        # ====================================================

        if (
            stage1_status
            == "needs_additional_evaluation"
        ):

            if sdg not in stage2_lookup:

                raise ValueError(
                    f"{course_code} - {sdg} "
                    f"was marked for Stage 2, "
                    f"but no Stage 2 result exists."
                )

            stage2_item = stage2_lookup[
                sdg
            ]

            final_score = int(
                stage2_item[
                    "final_score"
                ]
            )

            final_category = (
                stage2_item[
                    "final_category"
                ]
            )

            final_status = (
                stage2_item[
                    "status"
                ]
            )

            source = "stage2"

            reliability = (
                build_stage2_reliability(
                    stage2_item
                )
            )

        # ====================================================
        # CASE 2:
        # PAIR WAS RESOLVED IN STAGE 1
        # ====================================================

        else:

            final_score = int(
                stage1_item[
                    "representative_score"
                ]
            )

            final_category = (
                stage1_item[
                    "representative_category"
                ]
            )

            final_status = (
                stage1_status
            )

            source = "stage1"

            reliability = (
                build_stage1_reliability(
                    stage1_item
                )
            )

        # ====================================================
        # CONSISTENCY CHECK
        # ====================================================

        validate_final_score_category(
            course_code=course_code,
            sdg=sdg,
            score=final_score,
            category=final_category,
        )

        # ====================================================
        # FINAL SDG OBJECT
        # ====================================================

        final_evaluations.append(
            {
                "SDGInfo":
                    sdg,

                "correlation":
                    final_score,

                "category":
                    final_category,

                "status":
                    final_status,

                "source":
                    source,

                "reliability":
                    reliability,
            }
        )

    # --------------------------------------------------------
    # SORT SDG1 -> SDG16
    # --------------------------------------------------------

    final_evaluations.sort(
        key=lambda item:
        sdg_number(
            item["SDGInfo"]
        )
    )

    # --------------------------------------------------------
    # FINAL VALIDATION
    # --------------------------------------------------------

    if len(final_evaluations) != 16:

        raise ValueError(
            f"Final evaluation must contain "
            f"16 SDGs, but received "
            f"{len(final_evaluations)}."
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    status_counts = Counter(
        item["status"]
        for item in final_evaluations
    )

    source_counts = Counter(
        item["source"]
        for item in final_evaluations
    )

    summary = {
        "total_sdgs":
            len(final_evaluations),

        "status_counts":
            dict(status_counts),

        "source_counts":
            dict(source_counts),

        "stage1_resolved":
            source_counts.get(
                "stage1",
                0,
            ),

        "stage2_resolved":
            source_counts.get(
                "stage2",
                0,
            ),
    }

    # --------------------------------------------------------
    # FINAL COURSE OBJECT
    # --------------------------------------------------------

    return {
        "course":
            course_code,

        "evaluation":
            final_evaluations,

        "summary":
            summary,
    }