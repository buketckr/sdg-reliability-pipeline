import json
import os
import pandas as pd

from config import RUN


# --------------------------------------------------
# FILES
# --------------------------------------------------

INPUT_FILE = (
    f"method_a/stage3_results/run{RUN}/final_results.json"
)

OUTPUT_DIR = (
    f"method_a/final_results/run{RUN}/analysis"
)

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


def sdg_number(sdg):
    return int(
        sdg.replace("SDG", "")
    )


# --------------------------------------------------
# LOAD FINAL RESULT
# --------------------------------------------------

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as file:

    data = json.load(file)


# --------------------------------------------------
# CONVERT TO FLAT TABLE
# --------------------------------------------------

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

        source = evaluation.get(
            "source",
            "unknown"
        )

        rows.append({
            "course": course_code,
            "sdg": sdg,
            "score": score,
            "category": category,
            "source": source
        })


df = pd.DataFrame(rows)


# --------------------------------------------------
# BASIC SUMMARY
# --------------------------------------------------

total_courses = (
    df["course"]
    .nunique()
)

total_pairs = len(df)

print()
print(
    "========== FINAL RESULT ANALYSIS =========="
)

print(
    f"Total courses: {total_courses}"
)

print(
    f"Total course-SDG pairs: {total_pairs}"
)


# --------------------------------------------------
# CATEGORY DISTRIBUTION
# --------------------------------------------------

category_order = [
    "none/speculative",
    "indirect",
    "moderate",
    "SDG-inclusive",
    "SDG-focused"
]

category_counts = (
    df["category"]
    .value_counts()
    .reindex(
        category_order,
        fill_value=0
    )
)

category_percent = (
    category_counts
    / total_pairs
    * 100
)


category_summary = pd.DataFrame({
    "count": category_counts,
    "percent": category_percent
})


print()
print(
    "--- CATEGORY DISTRIBUTION ---"
)

print(
    category_summary.to_string()
)


category_summary.to_csv(
    f"{OUTPUT_DIR}/category_distribution.csv"
)


# --------------------------------------------------
# IMPORTANT RESULTS ONLY
# moderate / inclusive / focused
# --------------------------------------------------

important_categories = {
    "moderate",
    "SDG-inclusive",
    "SDG-focused"
}

important_df = df[
    df["category"].isin(
        important_categories
    )
].copy()


important_df = (
    important_df
    .sort_values(
        by=[
            "course",
            "score"
        ],
        ascending=[
            True,
            False
        ]
    )
)


important_df.to_csv(
    f"{OUTPUT_DIR}/important_results.csv",
    index=False
)


print()
print(
    "--- IMPORTANT RESULTS "
    "(MODERATE OR HIGHER) ---"
)

print(
    important_df[
        [
            "course",
            "sdg",
            "score",
            "category"
        ]
    ].to_string(
        index=False
    )
)


# --------------------------------------------------
# COURSE SUMMARY
# --------------------------------------------------

course_summary = (
    df.groupby(
        [
            "course",
            "category"
        ]
    )
    .size()
    .unstack(
        fill_value=0
    )
    .reindex(
        columns=category_order,
        fill_value=0
    )
)


course_summary[
    "important_total"
] = (
    course_summary[
        "moderate"
    ]
    + course_summary[
        "SDG-inclusive"
    ]
    + course_summary[
        "SDG-focused"
    ]
)


course_summary.to_csv(
    f"{OUTPUT_DIR}/course_summary.csv"
)


print()
print(
    "--- COURSE SUMMARY ---"
)

print(
    course_summary.to_string()
)


# --------------------------------------------------
# SDG SUMMARY
# --------------------------------------------------

sdg_summary = (
    df.groupby("sdg")
    .agg(
        mean_score=("score", "mean"),
        median_score=("score", "median"),
        max_score=("score", "max"),
        important_count=(
            "category",
            lambda x: x.isin(
                important_categories
            ).sum()
        )
    )
    .reset_index()
)


sdg_summary[
    "sdg_number"
] = (
    sdg_summary[
        "sdg"
    ]
    .apply(
        sdg_number
    )
)


sdg_summary = (
    sdg_summary
    .sort_values(
        "sdg_number"
    )
    .drop(
        columns=[
            "sdg_number"
        ]
    )
)


sdg_summary.to_csv(
    f"{OUTPUT_DIR}/sdg_summary.csv",
    index=False
)


print()
print(
    "--- SDG SUMMARY ---"
)

print(
    sdg_summary.to_string(
        index=False
    )
)


# --------------------------------------------------
# HIGHEST SCORES
# --------------------------------------------------

highest_scores = (
    df.sort_values(
        by="score",
        ascending=False
    )
    .head(20)
)


highest_scores.to_csv(
    f"{OUTPUT_DIR}/top_scores.csv",
    index=False
)


print()
print(
    "--- TOP 20 SCORES ---"
)

print(
    highest_scores[
        [
            "course",
            "sdg",
            "score",
            "category"
        ]
    ].to_string(
        index=False
    )
)


# --------------------------------------------------
# BOUNDARY CASES
# --------------------------------------------------

# Important category boundaries:
# 40/41
# 60/61
# 80/81

boundary_values = {
    39, 40, 41, 42,
    59, 60, 61, 62,
    79, 80, 81, 82
}

boundary_df = df[
    df["score"].isin(
        boundary_values
    )
].copy()


boundary_df = (
    boundary_df
    .sort_values(
        by=[
            "score",
            "course"
        ]
    )
)


boundary_df.to_csv(
    f"{OUTPUT_DIR}/boundary_cases.csv",
    index=False
)


print()
print(
    "--- BOUNDARY CASES ---"
)

if len(boundary_df) == 0:
    print(
        "No scores near selected category boundaries."
    )

else:
    print(
        boundary_df[
            [
                "course",
                "sdg",
                "score",
                "category"
            ]
        ].to_string(
            index=False
        )
    )


# --------------------------------------------------
# SOURCE SUMMARY
# --------------------------------------------------

if "source" in df.columns:

    source_summary = (
        df["source"]
        .value_counts()
        .rename_axis("source")
        .reset_index(
            name="count"
        )
    )

    source_summary.to_csv(
        f"{OUTPUT_DIR}/source_summary.csv",
        index=False
    )

    print()
    print(
        "--- RESULT SOURCE SUMMARY ---"
    )

    print(
        source_summary.to_string(
            index=False
        )
    )


# --------------------------------------------------
# SAVE FULL FLAT TABLE
# --------------------------------------------------

df.to_csv(
    f"{OUTPUT_DIR}/all_final_pairs.csv",
    index=False
)


print()
print(
    "Analysis files saved to:"
)

print(
    OUTPUT_DIR
)