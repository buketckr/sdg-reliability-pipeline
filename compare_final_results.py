import json
import os
from itertools import combinations

import pandas as pd


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

# Any number of files can be added.
FILES = {
    "run0": "method_a/stage3_results/frontend_run20/final_results.json",
    "run1": "method_a/stage3_results/frontend_run21/final_results.json",
    "run2": "method_a/stage3_results/frontend_run22/final_results.json",
    "run3": "method_a/stage3_results/frontend_run23/final_results.json",
    "run4": "method_a/stage3_results/frontend_run24/final_results.json",
    "run5": "method_a/stage3_results/frontend_run25/final_results.json",
 # "run0": "method_a/stage3_results/run2/final_results.json",
  # "run1": "method_a/stage3_results/run3/final_results.json",
   #"run2": "method_a/stage3_results/run6/final_results.json",
   #"run3": "method_a/stage3_results/run11/final_results.json",
    #"run4": "method_a/stage3_results/run16/final_results.json",
}

OUTPUT_DIR = "method_a/comparison_results_frontend20_21_22_23"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def get_category(score):
    if score <= 19:
        return "none/speculative"
    elif score <= 39:
        return "indirect"
    elif score <= 69:
        return "moderate"
    elif score <= 89:
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

            status = evaluation.get("status")

            rows.append({
                "course": course_code,
                "sdg": sdg,
                f"{label}_score": score,
                f"{label}_category": category,
                f"{label}_status": status
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

status_columns = [
    f"{label}_status"
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


def status_pattern(row):
    return " | ".join(
        f"{label}: {row[f'{label}_status']}"
        for label in labels
        if pd.notna(row[f"{label}_status"])
    )


def all_values_agree(row, columns):
    values = [row[column] for column in columns if pd.notna(row[column])]
    return len(values) == len(columns) and len(set(values)) == 1


def max_category_distance(row):
    order = {
        "none/speculative": 0,
        "indirect": 1,
        "moderate": 2,
        "SDG-inclusive": 3,
        "SDG-focused": 4
    }
    values = [row[column] for column in category_columns if pd.notna(row[column])]
    if len(values) < 2:
        return 0
    indices = [order[value] for value in values]
    return max(indices) - min(indices)


def only_none_indirect_variation(row):
    values = {row[column] for column in category_columns if pd.notna(row[column])}
    return len(values) > 1 and values.issubset({"none/speculative", "indirect"})


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

comparison_df["status_pattern"] = comparison_df.apply(status_pattern, axis=1)
comparison_df["all_scores_agree"] = comparison_df.apply(
    lambda row: all_values_agree(row, score_columns), axis=1
)
comparison_df["all_statuses_agree"] = comparison_df.apply(
    lambda row: all_values_agree(row, status_columns), axis=1
)
comparison_df["max_category_distance"] = comparison_df.apply(
    max_category_distance, axis=1
)
comparison_df["only_none_indirect_variation"] = comparison_df.apply(
    only_none_indirect_variation, axis=1
)
comparison_df["higher_impact_category_variation"] = (
    (~comparison_df["all_categories_agree"])
    & (~comparison_df["only_none_indirect_variation"])
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

comparison_df["score_mean"] = comparison_df[score_columns].mean(axis=1, skipna=True)
comparison_df["score_std_across_runs"] = comparison_df[score_columns].std(axis=1, skipna=True, ddof=1)


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


higher_impact_df = comparison_df[
    comparison_df["higher_impact_category_variation"]
].copy()

higher_impact_df.to_csv(
    f"{OUTPUT_DIR}/higher_impact_category_differences.csv",
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
            ].max(),

        "all_files_same_exact_score":
            int(comparison_df["all_scores_agree"].sum()),

        "exact_score_agreement_percent":
            float(comparison_df["all_scores_agree"].mean() * 100),

        "all_files_same_status":
            int(comparison_df["all_statuses_agree"].sum()),

        "status_agreement_percent":
            float(comparison_df["all_statuses_agree"].mean() * 100),

        "only_none_indirect_variation_pairs":
            int(comparison_df["only_none_indirect_variation"].sum()),

        "higher_impact_category_variation_pairs":
            int(comparison_df["higher_impact_category_variation"].sum())
    }
])


summary_df.to_csv(
    f"{OUTPUT_DIR}/comparison_summary.csv",
    index=False
)


# --------------------------------------------------
# PAIRWISE AGREEMENT
# --------------------------------------------------

pairwise_rows = []

for label1, label2 in combinations(labels, 2):
    cat1 = f"{label1}_category"
    cat2 = f"{label2}_category"
    score1 = f"{label1}_score"
    score2 = f"{label2}_score"
    status1 = f"{label1}_status"
    status2 = f"{label2}_status"

    valid = comparison_df[
        comparison_df[cat1].notna() & comparison_df[cat2].notna()
    ].copy()

    if len(valid) == 0:
        continue

    same_category = valid[cat1] == valid[cat2]
    same_score = valid[score1] == valid[score2]
    abs_diff = (valid[score1] - valid[score2]).abs()

    valid_status = valid[
        valid[status1].notna() & valid[status2].notna()
    ].copy()

    higher_impact_count = 0
    for _, row in valid.loc[~same_category].iterrows():
        cats = {row[cat1], row[cat2]}
        if not cats.issubset({"none/speculative", "indirect"}):
            higher_impact_count += 1

    pairwise_rows.append({
        "file_1": label1,
        "file_2": label2,
        "compared_pairs": len(valid),
        "same_category_pairs": int(same_category.sum()),
        "different_category_pairs": int((~same_category).sum()),
        "category_agreement_percent": float(same_category.mean() * 100),
        "same_exact_score_pairs": int(same_score.sum()),
        "exact_score_agreement_percent": float(same_score.mean() * 100),
        "mean_absolute_score_difference": float(abs_diff.mean()),
        "median_absolute_score_difference": float(abs_diff.median()),
        "max_absolute_score_difference": float(abs_diff.max()),
        "same_status_pairs": int((valid_status[status1] == valid_status[status2]).sum()) if len(valid_status) else 0,
        "status_agreement_percent": float((valid_status[status1] == valid_status[status2]).mean() * 100) if len(valid_status) else None,
        "higher_impact_category_differences": higher_impact_count
    })

pairwise_df = pd.DataFrame(pairwise_rows)
pairwise_df.to_csv(
    f"{OUTPUT_DIR}/pairwise_agreement.csv",
    index=False
)


# --------------------------------------------------
# CATEGORY TRANSITIONS
# --------------------------------------------------

transition_rows = []

for label1, label2 in combinations(labels, 2):
    cat1 = f"{label1}_category"
    cat2 = f"{label2}_category"

    valid = comparison_df[
        comparison_df[cat1].notna() & comparison_df[cat2].notna()
    ].copy()

    grouped = valid.groupby([cat1, cat2]).size().reset_index(name="count")

    for _, row in grouped.iterrows():
        transition_rows.append({
            "file_1": label1,
            "file_2": label2,
            "category_1": row[cat1],
            "category_2": row[cat2],
            "count": int(row["count"])
        })

transition_df = pd.DataFrame(transition_rows)
transition_df.to_csv(
    f"{OUTPUT_DIR}/category_transitions.csv",
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
    f"Same exact score in all files: "
    f"{int(comparison_df['all_scores_agree'].sum())}/{total_pairs} "
    f"({comparison_df['all_scores_agree'].mean() * 100:.2f}%)"
)

print(
    f"Same status in all files: "
    f"{int(comparison_df['all_statuses_agree'].sum())}/{total_pairs} "
    f"({comparison_df['all_statuses_agree'].mean() * 100:.2f}%)"
)

print(
    f"Only none/speculative <-> indirect variation: "
    f"{int(comparison_df['only_none_indirect_variation'].sum())}"
)

print(
    f"Higher-impact category variation: "
    f"{int(comparison_df['higher_impact_category_variation'].sum())}"
)

print()
print("--- HIGHER-IMPACT CATEGORY DIFFERENCES ---")

if len(higher_impact_df) == 0:
    print("No higher-impact category differences found.")
else:
    print(
        higher_impact_df[[
            "course",
            "sdg",
            "category_pattern",
            "score_pattern",
            "score_range",
            "max_category_distance"
        ]].to_string(index=False)
    )

print()
print(
    f"Comparison files saved to: "
    f"{OUTPUT_DIR}"
)
