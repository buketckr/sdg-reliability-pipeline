import json
import os
import re

import numpy as np
import pandas as pd

from config import RUN

NUM_RUNS = 5
INPUT_DIR = f"method_a/runs/run{RUN}"
FILES = [f"{INPUT_DIR}/run{i}.json" for i in range(1, NUM_RUNS + 1)]
OUTPUT_DIR = f"method_a/stage1_results/run{RUN}"
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_DETAIL = f"{OUTPUT_DIR}/details.csv"
OUTPUT_UNRESOLVED = f"{OUTPUT_DIR}/unresolved_pairs.json"
OUTPUT_UNRESOLVED_COURSES = f"{OUTPUT_DIR}/unresolved_courses.json"
OUTPUT_BORDERLINE = f"{OUTPUT_DIR}/borderline_pairs.json"
OUTPUT_SUMMARY = f"{OUTPUT_DIR}/summary.csv"

BOUNDARY_MARGIN = 3

for filename in FILES:
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Missing Stage 1 input file: {filename}")

CATEGORY_ORDER = [
    "none/speculative",
    "indirect",
    "moderate",
    "SDG-inclusive",
    "SDG-focused",
]


def normalize_sdg(value):
    match = re.search(r"SDG\s*(\d+)", str(value), re.IGNORECASE)
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
    return "SDG-focused"


def get_category_counts(categories):
    return {
        category: categories.count(category)
        for category in CATEGORY_ORDER
        if categories.count(category) > 0
    }


def get_dominant_category(categories):
    counts = get_category_counts(categories)
    max_count = max(counts.values())
    tied = [category for category, count in counts.items() if count == max_count]
    dominant = min(tied, key=lambda category: CATEGORY_ORDER.index(category))
    return dominant, max_count


def get_boundary_info(score):
    if 60 - BOUNDARY_MARGIN <= score <= 61 + BOUNDARY_MARGIN:
        return True, "moderate / SDG-inclusive"
    if 80 - BOUNDARY_MARGIN <= score <= 81 + BOUNDARY_MARGIN:
        return True, "SDG-inclusive / SDG-focused"
    return False, ""


def is_noncritical_low_variation(unique_categories):
    if unique_categories.issubset({"none/speculative", "indirect"}):
        return True
    if unique_categories.issubset({"indirect", "moderate"}):
        return True
    return False


rows = []
for run_number, filename in enumerate(FILES, start=1):
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    for course in data:
        course_code = course["course"]
        for evaluation in course["evaluation"]:
            sdg = normalize_sdg(evaluation["SDGInfo"])
            score = int(evaluation["correlation"])
            rows.append({
                "run": run_number,
                "course": course_code,
                "sdg": sdg,
                "score": score,
                "category": get_category(score),
            })


df = pd.DataFrame(rows)

pair_run_counts = df.groupby(["course", "sdg"])["run"].nunique()
bad_pairs = pair_run_counts[pair_run_counts != NUM_RUNS]
if len(bad_pairs) > 0:
    raise ValueError(
        f"Some course-SDG pairs do not have exactly {NUM_RUNS} runs:\n{bad_pairs}"
    )


result_rows = []
for (course, sdg), group in df.groupby(["course", "sdg"]):
    group = group.sort_values("run")
    scores = [int(value) for value in group["score"].tolist()]
    categories = group["category"].tolist()

    mean_score = float(np.mean(scores))
    median_score = int(np.median(scores))
    score_std = float(np.std(scores, ddof=1))
    score_range = int(max(scores) - min(scores))

    category_counts = get_category_counts(categories)
    dominant_category, dominant_count = get_dominant_category(categories)
    unique_categories = set(categories)

    representative_score = median_score
    representative_category = get_category(representative_score)

    boundary_flag = False
    boundary_between = ""

    if len(unique_categories) == 1:
        boundary_flag, boundary_between = get_boundary_info(representative_score)
        status = "borderline" if boundary_flag else "stable"
    elif is_noncritical_low_variation(unique_categories):
        status = "low_relevance_variation"
    else:
        status = "needs_additional_evaluation"

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
        "category_counts": json.dumps(category_counts, ensure_ascii=False),
        "dominant_category": dominant_category,
        "dominant_count": int(dominant_count),
        "representative_score": representative_score,
        "representative_category": representative_category,
        "mean_score": mean_score,
        "median_score": median_score,
        "score_std": score_std,
        "score_range": score_range,
        "boundary_flag": bool(boundary_flag),
        "boundary_between": boundary_between,
        "status": status,
    })


results = pd.DataFrame(result_rows)
results.to_csv(OUTPUT_DETAIL, index=False)


unresolved = results[results["status"] == "needs_additional_evaluation"].copy()
unresolved_records = []
for _, row in unresolved.iterrows():
    unresolved_records.append({
        "course": row["course"],
        "sdg": row["sdg"],
        "stage1_scores": [int(row[f"run{i}_score"]) for i in range(1, NUM_RUNS + 1)],
        "stage1_categories": [row[f"run{i}_category"] for i in range(1, NUM_RUNS + 1)],
        "stage1_dominant_category": row["dominant_category"],
        "stage1_dominant_count": int(row["dominant_count"]),
        "stage1_representative_score": int(row["representative_score"]),
        "stage1_representative_category": row["representative_category"],
    })

with open(OUTPUT_UNRESOLVED, "w", encoding="utf-8") as file:
    json.dump(unresolved_records, file, indent=4, ensure_ascii=False)


unresolved_course_map = {}
for item in unresolved_records:
    course_code = item["course"]
    if course_code not in unresolved_course_map:
        unresolved_course_map[course_code] = {
            "course": course_code,
            "problematic_sdgs": [],
        }
    unresolved_course_map[course_code]["problematic_sdgs"].append(item["sdg"])

unresolved_courses = list(unresolved_course_map.values())
for course_item in unresolved_courses:
    course_item["problematic_sdgs"] = sorted(
        course_item["problematic_sdgs"],
        key=lambda value: int(value.replace("SDG", "")),
    )

with open(OUTPUT_UNRESOLVED_COURSES, "w", encoding="utf-8") as file:
    json.dump(unresolved_courses, file, indent=4, ensure_ascii=False)


borderline = results[results["status"] == "borderline"].copy()
borderline_records = []
for _, row in borderline.iterrows():
    borderline_records.append({
        "course": row["course"],
        "sdg": row["sdg"],
        "scores": [int(row[f"run{i}_score"]) for i in range(1, NUM_RUNS + 1)],
        "category": row["representative_category"],
        "representative_score": int(row["representative_score"]),
        "boundary_between": row["boundary_between"],
    })

with open(OUTPUT_BORDERLINE, "w", encoding="utf-8") as file:
    json.dump(borderline_records, file, indent=4, ensure_ascii=False)


total_pairs = len(results)
stable_count = int((results["status"] == "stable").sum())
borderline_count = int((results["status"] == "borderline").sum())
low_variation_count = int((results["status"] == "low_relevance_variation").sum())
needs_extra_count = int((results["status"] == "needs_additional_evaluation").sum())

summary = pd.DataFrame([{
    "total_pairs": total_pairs,
    "stable": stable_count,
    "borderline": borderline_count,
    "low_relevance_variation": low_variation_count,
    "needs_additional_evaluation": needs_extra_count,
    "stable_percent": stable_count / total_pairs * 100,
    "stable_or_borderline_percent": (stable_count + borderline_count) / total_pairs * 100,
}])
summary.to_csv(OUTPUT_SUMMARY, index=False)


print("\n========== METHOD A - STAGE 1 ==========")
print(f"Run group: run{RUN}")
print(f"Total course-SDG pairs: {total_pairs}")
print(f"Stable: {stable_count}")
print(f"Borderline: {borderline_count}")
print(f"Low-relevance variation: {low_variation_count}")
print(f"Need Stage 2 evaluation: {needs_extra_count}")

print("\n--- BORDERLINE PAIRS ---")
if len(borderline) == 0:
    print("No borderline pairs.")
else:
    print(borderline[[
        "course", "sdg",
        "run1_score", "run2_score", "run3_score", "run4_score", "run5_score",
        "representative_category", "representative_score", "boundary_between"
    ]].to_string(index=False))

print("\n--- PAIRS SENT TO STAGE 2 ---")
if len(unresolved) == 0:
    print("No pairs require Stage 2.")
else:
    print(unresolved[[
        "course", "sdg",
        "run1_score", "run2_score", "run3_score", "run4_score", "run5_score",
        "category_counts", "representative_category"
    ]].to_string(index=False))

print("\n--- COURSES TO RE-EVALUATE IN STAGE 2 ---")
if len(unresolved_courses) == 0:
    print("No courses require Stage 2.")
else:
    for item in unresolved_courses:
        print(f"{item['course']}: {', '.join(item['problematic_sdgs'])}")

print(f"\nDetailed results: {OUTPUT_DETAIL}")
print(f"Unresolved pairs: {OUTPUT_UNRESOLVED}")
print(f"Stage 2 course list: {OUTPUT_UNRESOLVED_COURSES}")
print(f"Borderline pairs: {OUTPUT_BORDERLINE}")
print(f"Summary: {OUTPUT_SUMMARY}")
