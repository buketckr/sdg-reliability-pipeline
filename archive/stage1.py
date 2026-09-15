import json
import pandas as pd
import numpy as np
import re
import os
from config import RUN

# --------------------------------------------------
# INPUT FILES
# --------------------------------------------------

FILES = [
    f"method_a/runs/run{RUN}/run{i}.json"
    for i in range(1, 6)
]

for filename in FILES:
    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Missing Stage 1 input file: {filename}"
        )



OUTPUT_DIR = f"method_a/stage1_results/run{RUN}"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

OUTPUT_DETAIL = f"{OUTPUT_DIR}/details.csv"
OUTPUT_UNRESOLVED = f"{OUTPUT_DIR}/unresolved_pairs.json"
OUTPUT_SUMMARY = f"{OUTPUT_DIR}/summary.csv"

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def normalize_sdg(value):
    match = re.search(
        r"SDG\s*(\d+)",
        str(value),
        re.IGNORECASE
    )

    if match:
        return f"SDG{int(match.group(1))}"

    return str(value).strip()


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


# --------------------------------------------------
# READ 5 RUNS
# --------------------------------------------------

rows = []

for run_number, filename in enumerate(
    FILES,
    start=1
):

    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    for course in data:

        course_code = course["course"]

        for evaluation in course["evaluation"]:

            sdg = normalize_sdg(
                evaluation["SDGInfo"]
            )

            score = evaluation["correlation"]

            rows.append({
                "run": run_number,
                "course": course_code,
                "sdg": sdg,
                "score": score,
                "category": get_category(score)
            })


df = pd.DataFrame(rows)


# --------------------------------------------------
# ANALYZE EACH COURSE-SDG PAIR
# --------------------------------------------------

result_rows = []

for (course, sdg), group in df.groupby(
    ["course", "sdg"]
):

    group = group.sort_values("run")

    scores = group["score"].tolist()
    categories = group["category"].tolist()

    category_counts = (
        pd.Series(categories)
        .value_counts()
    )

    dominant_category = (
        category_counts.index[0]
    )

    dominant_count = int(
        category_counts.iloc[0]
    )

    mean_score = np.mean(scores)
    median_score = np.median(scores)
    score_std = np.std(
        scores,
        ddof=1
    )
    score_range = (
        max(scores) - min(scores)
    )

    # --------------------------------------------------
    # DECISION RULE
    # --------------------------------------------------

    CRITICAL_TRANSITIONS = [
        {"moderate", "SDG-inclusive"},
        {"SDG-inclusive", "SDG-focused"},
        {"moderate", "SDG-focused"}
    ]

    unique_categories = set(categories)

    if len(unique_categories) == 1:
        # All 5 runs produced the same category.
        status = "accepted"

    elif any(
        transition.issubset(unique_categories)
        for transition in CRITICAL_TRANSITIONS
    ):
        # Escalate only disagreements involving:
        # moderate <-> inclusive,
        # inclusive <-> focused,
        # moderate <-> focused.
        status = "needs_additional_evaluation"

    else:
        # Ignore lower-priority disagreements such as:
        # none/speculative <-> indirect
        # indirect <-> moderate
        status = "ignored_noncritical_disagreement"


    result_rows.append({
        "course": course,
        "sdg": sdg,

        "run1_score": scores[0],
        "run2_score": scores[1],
        "run3_score": scores[2],
        "run4_score": scores[3],
        "run5_score": scores[4],

        "run1_category": categories[0],
        "run2_category": categories[1],
        "run3_category": categories[2],
        "run4_category": categories[3],
        "run5_category": categories[4],

        "dominant_category":
            dominant_category,

        "dominant_count":
            dominant_count,

        "mean_score":
            mean_score,

        "median_score":
            median_score,

        "score_std":
            score_std,

        "score_range":
            score_range,

        "status":
            status
    })


results = pd.DataFrame(result_rows)


# --------------------------------------------------
# SAVE FULL DETAIL
# --------------------------------------------------

results.to_csv(
    OUTPUT_DETAIL,
    index=False
)


# --------------------------------------------------
# CREATE UNRESOLVED JSON
# --------------------------------------------------

unresolved = results[
    results["status"]
    ==
    "needs_additional_evaluation"
].copy()


unresolved_records = []

for _, row in unresolved.iterrows():

    unresolved_records.append({
        "course": row["course"],
        "sdg": row["sdg"],

        "existing_scores": [
            int(row["run1_score"]),
            int(row["run2_score"]),
            int(row["run3_score"]),
            int(row["run4_score"]),
            int(row["run5_score"])
        ],

        "existing_categories": [
            row["run1_category"],
            row["run2_category"],
            row["run3_category"],
            row["run4_category"],
            row["run5_category"]
        ],

        "dominant_category":
            row["dominant_category"],

        "dominant_count":
            int(row["dominant_count"])
    })


with open(
    OUTPUT_UNRESOLVED,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        unresolved_records,
        f,
        indent=4,
        ensure_ascii=False
    )


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

total_pairs = len(results)

accepted_count = (
    results["status"]
    == "accepted"
).sum()

needs_extra_count = (
    results["status"]
    ==
    "needs_additional_evaluation"
).sum()

ignored_count = (
    results["status"]
    ==
    "ignored_noncritical_disagreement"
).sum()


summary = pd.DataFrame([
    {
        "total_pairs":
            total_pairs,

        "accepted_5of5":
            accepted_count,

        "accepted_percent":
            accepted_count
            / total_pairs
            * 100,

        "needs_additional_evaluation":
            needs_extra_count,

        "ignored_noncritical_disagreement":
            ignored_count
    }
])


summary.to_csv(
    OUTPUT_SUMMARY,
    index=False
)


# --------------------------------------------------
# PRINT
# --------------------------------------------------

print("\n--- METHOD A RESULTS ---")

print(
    f"Total course-SDG pairs: "
    f"{total_pairs}"
)

print(
    f"Accepted with 5/5 category agreement: "
    f"{accepted_count}"
)

print(
    f"Need extra evaluation: "
    f"{needs_extra_count}"
)

print(
    f"Ignored non-critical disagreements: "
    f"{ignored_count}"
)


print("\n--- UNRESOLVED PAIRS ---")

if len(unresolved) == 0:
    print("No unresolved relevant pairs.")

else:

    print(
        unresolved[[
            "course",
            "sdg",
            "run1_score",
            "run2_score",
            "run3_score",
            "run4_score",
            "run5_score",
            "dominant_category",
            "dominant_count"
        ]].to_string(
            index=False
        )
    )


print(
    f"\nDetailed results saved to: "
    f"{OUTPUT_DETAIL}"
)

print(
    f"Unresolved pairs saved to: "
    f"{OUTPUT_UNRESOLVED}"
)