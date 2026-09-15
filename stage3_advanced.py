import json
import os

import numpy as np
import pandas as pd

from config import RUN


# --------------------------------------------------
# FILES
# --------------------------------------------------

OUTPUT_DIR = f"method_a/stage3_results/run{RUN}"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

STAGE1_DETAILS = (
    f"method_a/stage1_results/run{RUN}/details.csv"
)

STAGE2_RESULTS = (
    f"method_a/stage2_results/run{RUN}/results.json"
)

OUTPUT_FILE = (
    f"{OUTPUT_DIR}/final_results.json"
)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def get_category(score):

    if score <= 20:
        return "none/speculative"

    elif score <= 40:
        return "indirect"

    elif score <= 60:
        return "moderate"

    elif score <= 80:
        return "SDG-inclusive"

    else:
        return "SDG-focused"


def sdg_number(value):

    return int(
        str(value).replace(
            "SDG",
            ""
        )
    )


def safe_float(value):
    """
    Convert pandas / JSON numeric values to a normal Python float.
    NaN becomes None so the final JSON remains valid.
    """

    if value is None:
        return None

    try:
        numeric = float(value)

        if np.isnan(numeric):
            return None

        return numeric

    except (TypeError, ValueError):
        return None


def safe_int(value):

    if value is None:
        return None

    try:
        numeric = float(value)

        if np.isnan(numeric):
            return None

        return int(round(numeric))

    except (TypeError, ValueError):
        return None


def parse_category_counts(value):
    """
    Stage 1 stores category_counts as a JSON string inside details.csv.
    Convert it back to a dictionary for the final output.
    """

    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    try:
        return json.loads(value)

    except (TypeError, json.JSONDecodeError):
        return {}


# --------------------------------------------------
# VALIDATE INPUT
# --------------------------------------------------

if not os.path.exists(
    STAGE1_DETAILS
):

    raise FileNotFoundError(
        f"Stage 1 details file not found: "
        f"{STAGE1_DETAILS}"
    )


# --------------------------------------------------
# LOAD STAGE 1
# --------------------------------------------------

stage1 = pd.read_csv(
    STAGE1_DETAILS
)


# --------------------------------------------------
# LOAD STAGE 2
# --------------------------------------------------

if os.path.exists(
    STAGE2_RESULTS
):

    with open(
        STAGE2_RESULTS,
        "r",
        encoding="utf-8"
    ) as file:

        stage2 = json.load(
            file
        )

else:

    stage2 = []


stage2_lookup = {
    (
        item[
            "course"
        ],
        item[
            "sdg"
        ]
    ): item

    for item in stage2
}


# --------------------------------------------------
# CREATE FINAL RESULTS
# --------------------------------------------------

final_courses = {}


for _, row in stage1.iterrows():

    course = row[
        "course"
    ]

    sdg = row[
        "sdg"
    ]

    stage1_status = row[
        "status"
    ]

    key = (
        course,
        sdg
    )


    # --------------------------------------------------
    # CASE 1:
    # PAIR WAS SENT TO STAGE 2
    # --------------------------------------------------

    if (
        stage1_status
        == "needs_additional_evaluation"
    ):

        if key not in stage2_lookup:

            raise ValueError(
                f"{course} - {sdg} was marked for "
                f"Stage 2, but no Stage 2 result exists."
            )


        result = stage2_lookup[
            key
        ]


        final_score = int(
            result[
                "final_score"
            ]
        )

        final_category = result[
            "final_category"
        ]

        final_status = result[
            "status"
        ]

        source = "stage2"


        # Reliability metadata from Stage 2
        reliability = {
            "status":
                final_status,

            "combined_category_agreement":
                safe_float(
                    result.get(
                        "combined_category_agreement"
                    )
                ),

            "ci_95_lower":
                safe_float(
                    result.get(
                        "ci_95_lower"
                    )
                ),

            "ci_95_upper":
                safe_float(
                    result.get(
                        "ci_95_upper"
                    )
                ),

            "ci_half_width":
                safe_float(
                    result.get(
                        "ci_half_width"
                    )
                ),

            "ci_inside_final_category":
                bool(
                    result.get(
                        "ci_inside_final_category",
                        False
                    )
                ),

            "boundary_sensitive":
                bool(
                    result.get(
                        "boundary_sensitive",
                        False
                    )
                ),

            "reliability_level":
                result.get(
                    "reliability_level"
                ),

            "stage2_supports_final_category":
                bool(
                    result.get(
                        "stage2_supports_final_category",
                        False
                    )
                ),

            "stage1_dominant_category":
                result.get(
                    "stage1_dominant_category"
                ),

            "stage2_dominant_category":
                result.get(
                    "stage2_dominant_category"
                ),

            "cross_stage_category_distance":
                safe_int(
                    result.get(
                        "cross_stage_category_distance"
                    )
                ),

            "stage1_scores":
                result.get(
                    "stage1_scores",
                    []
                ),

            "stage2_scores":
                result.get(
                    "stage2_scores",
                    []
                )
        }


    # --------------------------------------------------
    # CASE 2:
    # PAIR WAS RESOLVED IN STAGE 1
    # --------------------------------------------------

    else:

        # New Stage 1 already creates a representative score/category.
        # Use those directly so the numeric score and category always agree.
        if (
            "representative_score"
            in row.index
            and not pd.isna(
                row[
                    "representative_score"
                ]
            )
        ):

            final_score = int(
                row[
                    "representative_score"
                ]
            )

        else:

            scores = [
                row[
                    f"run{i}_score"
                ]
                for i in range(
                    1,
                    6
                )
            ]

            final_score = int(
                round(
                    np.median(
                        scores
                    )
                )
            )


        if (
            "representative_category"
            in row.index
            and not pd.isna(
                row[
                    "representative_category"
                ]
            )
        ):

            final_category = row[
                "representative_category"
            ]

        else:

            final_category = (
                get_category(
                    final_score
                )
            )


        final_status = (
            stage1_status
        )

        source = "stage1"


        reliability = {
            "status":
                final_status,

            "category_agreement":
                (
                    safe_int(
                        row.get(
                            "dominant_count"
                        )
                    )
                    / 5
                )
                if safe_int(
                    row.get(
                        "dominant_count"
                    )
                ) is not None
                else None,

            "dominant_category":
                row.get(
                    "dominant_category"
                ),

            "category_counts":
                parse_category_counts(
                    row.get(
                        "category_counts"
                    )
                ),

            "boundary_flag":
                bool(
                    row.get(
                        "boundary_flag",
                        False
                    )
                ),

            "boundary_between":
                (
                    None
                    if pd.isna(
                        row.get(
                            "boundary_between"
                        )
                    )
                    else row.get(
                        "boundary_between"
                    )
                ),

            "score_std":
                safe_float(
                    row.get(
                        "score_std"
                    )
                ),

            "score_range":
                safe_int(
                    row.get(
                        "score_range"
                    )
                )
        }


    # --------------------------------------------------
    # INTERNAL CONSISTENCY CHECK
    # --------------------------------------------------

    score_category = (
        get_category(
            final_score
        )
    )


    if (
        score_category
        != final_category
    ):

        raise ValueError(
            f"Inconsistent final result for "
            f"{course} - {sdg}: "
            f"score {final_score} maps to "
            f"'{score_category}', but final category "
            f"is '{final_category}'."
        )


    # --------------------------------------------------
    # CREATE COURSE OBJECT
    # --------------------------------------------------

    if course not in final_courses:

        final_courses[
            course
        ] = {
            "course":
                course,

            "evaluation":
                []
        }


    final_courses[
        course
    ][
        "evaluation"
    ].append({
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
            reliability
    })


# --------------------------------------------------
# SORT SDGS
# --------------------------------------------------

for course_data in final_courses.values():

    course_data[
        "evaluation"
    ].sort(
        key=lambda item:
            sdg_number(
                item[
                    "SDGInfo"
                ]
            )
    )


# --------------------------------------------------
# SAVE FINAL JSON
# --------------------------------------------------

final_output = list(
    final_courses.values()
)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        final_output,
        file,
        indent=4,
        ensure_ascii=False,
        allow_nan=False
    )


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

status_counts = {}


for course_data in final_output:

    for evaluation in course_data[
        "evaluation"
    ]:

        status = evaluation[
            "status"
        ]

        status_counts[
            status
        ] = (
            status_counts.get(
                status,
                0
            )
            + 1
        )


print()
print(
    "========== METHOD A - STAGE 3 =========="
)

print(
    f"Final results saved to: "
    f"{OUTPUT_FILE}"
)

print(
    f"Courses: "
    f"{len(final_output)}"
)

print()
print(
    "Status counts:"
)

for status, count in sorted(
    status_counts.items()
):

    print(
        f"  {status}: {count}"
    )
