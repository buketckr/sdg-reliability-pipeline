import json
import os
from itertools import combinations

import pandas as pd


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

# Add as many final-result JSON files as you want.
# Two, three, four, etc. are all supported.
FILES = {
    "run0": "method_a/stage3_results/run3/final_results.json",
    "run1": "method_a/stage3_results/run4/final_results.json",
    "run2": "method_a/stage3_results/run6/final_results.json",
    # "run4": "method_a/final_results/run4/final_result.json",
}

OUTPUT_DIR = "method_a/comparison_results"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
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


def load_final_result(label, filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"File not found for {label}: {filepath}"
        )

    with open(
        filepath,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    rows = []

    for course in data:
        course_code = course["course"]

        for evaluation in course["evaluation"]:
            sdg = evaluation["SDGInfo"]
            score = int(
                evaluation["correlation"]
            )

            category = evaluation.get(
                "category",
                get_category(score)
            )

            rows.append({
                "course": course_code,
                "sdg": sdg,
                f"{label}_score": score,
                f"{label}_category": category
            })

    return pd.DataFrame(rows)


# --------------------------------------------------
# LOAD ALL FILES
# --------------------------------------------------

if len(FILES) < 2:
    raise ValueError(
        "At least two files are required for comparison."
    )


comparison_df = None


for label, filepath in FILES.items():

    current_df = load_final_result(
        label,
        filepath
    )

    if comparison_df is None:
        comparison_df = current_df

    else:
        comparison_df = comparison_df.merge(
            current_df,
            on=[
                "course",
                "sdg"
            ],
            how="outer"
        )


# --------------------------------------------------
# CHECK CATEGORY AGREEMENT
# --------------------------------------------------

labels = list(
    FILES.keys()
)

category_columns = [
    f"{label}_category"
    for label in labels
]

score_columns = [
    f"{label}_score"
    for label in labels
]


def category_agreement(row):
    values = [
        row[column]
        for column in category_columns
        if pd.notna(row[column])
    ]

    return (
        len(set(values)) == 1
        if values
        else False
    )


def number_of_unique_categories(row):
    values = [
        row[column]
        for column in category_columns
        if pd.notna(row[column])
    ]

    return len(
        set(values)
    )


def category_pattern(row):
    return " | ".join(
        f"{label}: {row[f'{label}_category']}"
        for label in labels
        if pd.notna(
            row[f"{label}_category"]
        )
    )


def score_pattern(row):
    return " | ".join(
        f"{label}: {int(row[f'{label}_score'])}"
        for label in labels
        if pd.notna(
            row[f"{label}_score"]
        )
    )


comparison_df[
    "all_categories_agree"
] = comparison_df.apply(
    category_agreement,
    axis=1
)

comparison_df[
    "unique_category_count"
] = comparison_df.apply(
    number_of_unique_categories,
    axis=1
)

comparison_df[
    "category_pattern"
] = comparison_df.apply(
    category_pattern,
    axis=1
)

comparison_df[
    "score_pattern"
] = comparison_df.apply(
    score_pattern,
    axis=1
)


# --------------------------------------------------
# SCORE RANGE ACROSS FILES
# --------------------------------------------------

comparison_df[
    "score_min"
] = comparison_df[
    score_columns
].min(
    axis=1,
    skipna=True
)

comparison_df[
    "score_max"
] = comparison_df[
    score_columns
].max(
    axis=1,
    skipna=True
)

comparison_df[
    "score_range"
] = (
    comparison_df[
        "score_max"
    ]
    -
    comparison_df[
        "score_min"
    ]
)


# --------------------------------------------------
# SAVE FULL COMPARISON
# --------------------------------------------------

comparison_df = (
    comparison_df
    .sort_values(
        by=[
            "course",
            "sdg"
        ]
    )
)


comparison_df.to_csv(
    f"{OUTPUT_DIR}/all_comparisons.csv",
    index=False
)


# --------------------------------------------------
# CATEGORY DIFFERENCES ONLY
# --------------------------------------------------

differences_df = comparison_df[
    comparison_df[
        "all_categories_agree"
    ] == False
].copy()


differences_df.to_csv(
    f"{OUTPUT_DIR}/category_differences.csv",
    index=False
)


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

total_pairs = len(
    comparison_df
)

agree_count = int(
    comparison_df[
        "all_categories_agree"
    ].sum()
)

difference_count = (
    total_pairs
    - agree_count
)

agreement_percent = (
    agree_count
    / total_pairs
    * 100
    if total_pairs > 0
    else 0
)


summary_df = pd.DataFrame([
    {
        "number_of_files":
            len(FILES),

        "total_course_sdg_pairs":
            total_pairs,

        "all_files_same_category":
            agree_count,

        "category_difference_pairs":
            difference_count,

        "category_agreement_percent":
            agreement_percent,

        "mean_score_range":
            comparison_df[
                "score_range"
            ].mean(),

        "median_score_range":
            comparison_df[
                "score_range"
            ].median(),

        "max_score_range":
            comparison_df[
                "score_range"
            ].max()
    }
])


summary_df.to_csv(
    f"{OUTPUT_DIR}/comparison_summary.csv",
    index=False
)


# --------------------------------------------------
# PAIRWISE CATEGORY AGREEMENT
# --------------------------------------------------

pairwise_rows = []


for label1, label2 in combinations(
    labels,
    2
):

    col1 = f"{label1}_category"
    col2 = f"{label2}_category"

    valid = comparison_df[
        comparison_df[col1].notna()
        &
        comparison_df[col2].notna()
    ].copy()

    if len(valid) == 0:
        agreement = None
        same_count = 0

    else:
        same = (
            valid[col1]
            == valid[col2]
        )

        same_count = int(
            same.sum()
        )

        agreement = (
            same_count
            / len(valid)
            * 100
        )


    pairwise_rows.append({
        "file_1": label1,
        "file_2": label2,
        "compared_pairs": len(valid),
        "same_category_pairs": same_count,
        "different_category_pairs":
            len(valid) - same_count,
        "category_agreement_percent":
            agreement
    })


pairwise_df = pd.DataFrame(
    pairwise_rows
)


pairwise_df.to_csv(
    f"{OUTPUT_DIR}/pairwise_agreement.csv",
    index=False
)


# --------------------------------------------------
# PRINT RESULTS
# --------------------------------------------------

print()
print(
    "========== FINAL RESULT COMPARISON =========="
)

print(
    f"Files compared: {len(FILES)}"
)

print(
    f"Total course-SDG pairs: {total_pairs}"
)

print(
    f"Same category in all files: "
    f"{agree_count}"
)

print(
    f"Category differences: "
    f"{difference_count}"
)

print(
    f"Overall category agreement: "
    f"{agreement_percent:.2f}%"
)


print()
print(
    "--- PAIRWISE AGREEMENT ---"
)

print(
    pairwise_df.to_string(
        index=False
    )
)


print()
print(
    "--- CATEGORY DIFFERENCES ---"
)

if len(
    differences_df
) == 0:

    print(
        "No category differences found."
    )

else:

    columns_to_print = [
        "course",
        "sdg",
        "category_pattern",
        "score_pattern",
        "score_range"
    ]

    print(
        differences_df[
            columns_to_print
        ].to_string(
            index=False
        )
    )


print()
print(
    f"Comparison files saved to: "
    f"{OUTPUT_DIR}"
)
