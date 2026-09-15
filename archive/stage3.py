import json
import pandas as pd
import numpy as np
import os
from config import RUN


# --------------------------------------------------
# FILES
# --------------------------------------------------

OUTPUT_DIR = f"method_a/stage3_results/run{RUN}"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


METHOD_A_DETAIL = f"method_a/stage1_results/run{RUN}/detailS.csv"
STAGE2_RESULTS = f"method_a/stage2_results/run{RUN}/results.json"

OUTPUT_FILE = f"{OUTPUT_DIR}/final_results.json"


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


# --------------------------------------------------
# LOAD STAGE 1 RESULTS
# --------------------------------------------------

stage1 = pd.read_csv(
    METHOD_A_DETAIL
)


# --------------------------------------------------
# LOAD STAGE 2 RESULTS
# --------------------------------------------------

try:
    with open(
        STAGE2_RESULTS,
        "r",
        encoding="utf-8"
    ) as file:
        stage2 = json.load(file)

except FileNotFoundError:
    stage2 = []


# Create lookup:
# ("ECON 321", "SDG10") -> stage2 result
stage2_lookup = {
    (
        item["course"],
        item["sdg"]
    ): item
    for item in stage2
}


# --------------------------------------------------
# CREATE FINAL RESULTS
# --------------------------------------------------

final_courses = {}


for _, row in stage1.iterrows():

    course = row["course"]
    sdg = row["sdg"]

    key = (
        course,
        sdg
    )


    # --------------------------------------------------
    # IF STAGE 2 EXISTS, USE STAGE 2 RESULT
    # --------------------------------------------------

    if key in stage2_lookup:

        result = stage2_lookup[key]

        final_score = round(
            result["mean_score"]
        )

        final_category = (
            result["dominant_category"]
        )

        source = "stage2"


    # --------------------------------------------------
    # OTHERWISE USE STAGE 1 RESULT
    # --------------------------------------------------

    else:

        scores = [
            row["run1_score"],
            row["run2_score"],
            row["run3_score"],
            row["run4_score"],
            row["run5_score"]
        ]

        # Median is robust against one unusual run
        final_score = int(
            round(
                np.median(scores)
            )
        )

        final_category = (
            row["dominant_category"]
        )

        source = "stage1"


    # --------------------------------------------------
    # CREATE COURSE OBJECT
    # --------------------------------------------------

    if course not in final_courses:

        final_courses[course] = {
            "course": course,
            "evaluation": []
        }


    final_courses[course][
        "evaluation"
    ].append({
        "SDGInfo": sdg,
        "correlation": final_score,
        "category": final_category,
        "source": source
    })


# --------------------------------------------------
# SORT SDGS
# --------------------------------------------------

def sdg_number(value):
    return int(
        value.replace(
            "SDG",
            ""
        )
    )


for course_data in final_courses.values():

    course_data[
        "evaluation"
    ].sort(
        key=lambda x:
            sdg_number(
                x["SDGInfo"]
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
        ensure_ascii=False
    )


print(
    f"Final results saved to: "
    f"{OUTPUT_FILE}"
)

print(
    f"Courses: "
    f"{len(final_output)}"
)