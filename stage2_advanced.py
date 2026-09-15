import json
import os
import time
import csv
import statistics
import math
from collections import Counter

from scipy import stats

from dotenv import load_dotenv
from openai import OpenAI

from config import RUN


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

MODEL = "gpt-5.4"

# Stage 2 now uses the SAME full SDG1-SDG16 evaluation context
# as Stage 1.
EXTRA_FULL_RUNS = 3

# With 5 Stage 1 runs + 3 Stage 2 runs = 8 total observations,
# require at least 75% agreement (6/8) for stable_after_recheck.
MIN_COMBINED_CATEGORY_AGREEMENT = 0.75

# CI is now used as reliability / uncertainty information only.
# It does NOT veto the final category decision.
#
# Stage 2 stability is determined by:
#   1) combined category agreement >= 75%
#   2) Stage 2 dominant category == combined dominant category
#
# The 95% CI is still calculated and reported so that the final
# result can communicate how numerically boundary-sensitive it is.

STAGE1_DIR = f"method_a/stage1_results/run{RUN}"
OUTPUT_DIR = f"method_a/stage2_results/run{RUN}"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

UNRESOLVED_PAIRS_FILE = (
    f"{STAGE1_DIR}/unresolved_pairs.json"
)

UNRESOLVED_COURSES_FILE = (
    f"{STAGE1_DIR}/unresolved_courses.json"
)

COURSES_FILE = "data/filtered_courses.json"

OUTPUT_FILE = (
    f"{OUTPUT_DIR}/results.json"
)

RAW_STAGE2_RUNS_FILE = (
    f"{OUTPUT_DIR}/raw_full_runs.json"
)

TOKEN_LOG_FILE = (
    f"{OUTPUT_DIR}/token_usage.csv"
)


# --------------------------------------------------
# OPENAI
# --------------------------------------------------

load_dotenv()

client = OpenAI(
    api_key=os.getenv("API_KEY")
)


# --------------------------------------------------
# PROMPT
# --------------------------------------------------

# IMPORTANT:
# Keep this prompt aligned with AI.py / Stage 1.
# Stage 2 should not switch to a pair-specific prompt.

promptTemplate = (
    "Evaluate the course description and learning outcomes against SDG1 through SDG16 in numerical order. Do not evaluate SDG17. "

    "For each SDG, return SDGInfo and correlation. "
    "Use SDGInfo in the format 'SDG<number>'. "
    "Set correlation to an integer from 0 to 100, where higher values mean stronger correlation and alignment. "

    "Treat evidence as direct only when the course description or learning outcomes explicitly and substantively address the SDG. "
    "Treat hypothetical applications, transferable skills, general societal benefits, and downstream effects as indirect evidence. "
    "Do not infer alignment solely from content related to a neighboring or conceptually similar SDG. "
    "Evidence must specifically support the SDG being evaluated. "

    "Use these scoring categories consistently: "
    "0-20 = no meaningful or only speculative relationship (0 <= score <= 20). "
    "21-40 = indirect relationship (21 <= score <= 40). "
    "41-60 = moderate relationship; some explicit SDG-related content is present, but not enough to classify the course as SDG-inclusive (41 <= score <= 60). "
    "61-80 = SDG-inclusive; the SDG is clearly and substantively incorporated into the course, but is not its primary focus (61 <= score <= 80). "
    "81-100 = SDG-focused; the SDG is a central or primary focus of the course (81 <= score <= 100). "

    "Apply the boundaries exactly: "
    "40 is indirect, 41 is moderate, 60 is moderate, 61 is SDG-inclusive, 80 is SDG-inclusive, and 81 is SDG-focused. "

    "Apply the scoring categories as sequential decision gates. "
    "First determine whether there is explicit SDG-specific evidence in the course description or learning outcomes. "
    "If there is no explicit SDG-specific evidence, the score must not exceed 40, even if the course could contribute to the SDG in practice. "

    "If explicit SDG-specific evidence exists, determine whether it is substantive and integrated into the course. "
    "If the evidence is explicit but limited, peripheral, or only briefly mentioned, the score must not exceed 60. "
    "Only explicit and substantive SDG-specific evidence may receive a score above 60. "

    "Finally, determine whether the SDG-related theme characterizes the course as a whole. "
    "A score above 80 may be assigned only when the SDG is a central or primary focus of the course, rather than one important topic among several. "

    "Do not classify a relationship as indirect (21-40) when the course explicitly and substantively addresses content that is part of the SDG. "
    "Do not assign strong relevance based only on indirect evidence. "

    "For SDG4, being a higher-education course is not itself evidence of alignment. "
    "Assign substantial SDG4 relevance only when the course explicitly addresses educational quality, access to education, teaching or learning methods, education policy, educational technologies, or another substantive aspect of SDG4. "

    "Include every SDG from SDG1 through SDG16. "

    "Return only valid JSON in this format: "
    '{"evaluation":[{"SDGInfo":"SDG1","correlation":0}]}'
)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

CATEGORY_ORDER = [
    "none/speculative",
    "indirect",
    "moderate",
    "SDG-inclusive",
    "SDG-focused"
]


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


def get_category_bounds(category):

    if category == "none/speculative":
        return 0, 20

    elif category == "indirect":
        return 21, 40

    elif category == "moderate":
        return 41, 60

    elif category == "SDG-inclusive":
        return 61, 80

    elif category == "SDG-focused":
        return 81, 100

    raise ValueError(
        f"Unknown category: {category}"
    )


def calculate_confidence_interval(scores):
    """
    95% Student-t confidence interval for the mean score across
    repeated full-context evaluations.

    This describes uncertainty in the mean model score; it is NOT
    a probability that the 'true SDG relevance' lies in this interval.
    """

    n = len(scores)

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
            "ci_half_width": None
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
            "ci_half_width": 0.0
        }

    standard_error = (
        std
        / math.sqrt(n)
    )

    t_critical = float(
        stats.t.ppf(
            0.975,
            df=n - 1
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
        "ci_half_width": margin
    }


def category_distance(category_a, category_b):

    return abs(
        CATEGORY_ORDER.index(category_a)
        - CATEGORY_ORDER.index(category_b)
    )


def dominant_category(categories):
    """
    Returns:
        dominant category,
        count,
        agreement ratio

    Tie-break is deterministic: lower category wins the tie.
    """

    counts = Counter(
        categories
    )

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
        key=lambda category:
            CATEGORY_ORDER.index(category)
    )

    return (
        dominant,
        int(max_count),
        float(
            max_count
            / len(categories)
        )
    )


def representative_score_for_category(
    scores,
    category
):
    """
    Final score is calculated only from scores that belong to
    the selected final category.

    This prevents impossible combinations such as:
        score = 46
        category = indirect
    """

    matching_scores = [
        int(score)
        for score in scores
        if get_category(
            int(score)
        ) == category
    ]

    if not matching_scores:
        return None

    return int(
        statistics.median(
            matching_scores
        )
    )


def clean_json(response_text):

    start = response_text.find("{")
    end = response_text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "No JSON object found in model response."
        )

    cleaned = response_text[
        start:end + 1
    ]

    cleaned = (
        cleaned
        .replace(
            "```json",
            ""
        )
        .replace(
            "```",
            ""
        )
        .strip()
    )

    return cleaned


def evaluation_to_lookup(
    evaluation_list
):

    lookup = {}

    for item in evaluation_list:

        sdg = str(
            item[
                "SDGInfo"
            ]
        ).replace(
            " ",
            ""
        )

        score = int(
            item[
                "correlation"
            ]
        )

        lookup[
            sdg
        ] = score

    return lookup


# --------------------------------------------------
# LOAD STAGE 1 INPUTS
# --------------------------------------------------

for required_file in [
    UNRESOLVED_PAIRS_FILE,
    UNRESOLVED_COURSES_FILE,
    COURSES_FILE
]:

    if not os.path.exists(
        required_file
    ):

        raise FileNotFoundError(
            f"Required file not found: {required_file}"
        )


with open(
    UNRESOLVED_PAIRS_FILE,
    "r",
    encoding="utf-8"
) as file:

    unresolved_pairs = json.load(
        file
    )


with open(
    UNRESOLVED_COURSES_FILE,
    "r",
    encoding="utf-8"
) as file:

    unresolved_courses = json.load(
        file
    )


with open(
    COURSES_FILE,
    "r",
    encoding="utf-8"
) as file:

    course_catalog = json.load(
        file
    )


course_lookup = {
    course[
        "courseCode"
    ]: course

    for course in course_catalog
}


# --------------------------------------------------
# STAGE 1 PAIR LOOKUP
# --------------------------------------------------

stage1_pair_lookup = {
    (
        item[
            "course"
        ],
        item[
            "sdg"
        ]
    ): item

    for item in unresolved_pairs
}


# --------------------------------------------------
# TOKEN LOG
# --------------------------------------------------

with open(
    TOKEN_LOG_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as token_file:

    writer = csv.writer(
        token_file
    )

    writer.writerow([
        "course",
        "stage2_run_number",
        "response_time_seconds",
        "input_tokens",
        "output_tokens",
        "total_tokens"
    ])


# --------------------------------------------------
# RUN STAGE 2
# --------------------------------------------------

raw_full_runs = {}

results = []


print()
print(
    "========== METHOD A - STAGE 2 =========="
)

print(
    f"Run group: run{RUN}"
)

print(
    f"Courses requiring Stage 2: "
    f"{len(unresolved_courses)}"
)


# --------------------------------------------------
# RE-EVALUATE EACH PROBLEMATIC COURSE
# --------------------------------------------------

for course_index, course_item in enumerate(
    unresolved_courses,
    start=1
):

    course_code = course_item[
        "course"
    ]

    problematic_sdgs = course_item[
        "problematic_sdgs"
    ]


    print()
    print(
        "=" * 60
    )

    print(
        f"Course "
        f"{course_index}/"
        f"{len(unresolved_courses)}: "
        f"{course_code}"
    )

    print(
        f"Problematic SDGs: "
        f"{', '.join(problematic_sdgs)}"
    )

    print(
        "=" * 60
    )


    course = course_lookup.get(
        course_code
    )

    if course is None:

        raise ValueError(
            f"{course_code} not found in "
            f"{COURSES_FILE}"
        )


    course_description = course.get(
        "courseDescEN",
        ""
    )

    learning_outcomes = " ".join(
        course.get(
            "learningOutcomes",
            []
        )
    )


    user_content = (
        f"Course Description: "
        f"{course_description}\n\n"
        f"Learning Outcomes: "
        f"{learning_outcomes}"
    )


    raw_full_runs[
        course_code
    ] = []


    # --------------------------------------------------
    # 3 EXTRA FULL SDG1-SDG16 RUNS
    # --------------------------------------------------

    for stage2_run_number in range(
        1,
        EXTRA_FULL_RUNS + 1
    ):

        print(
            f"Stage 2 full run "
            f"{stage2_run_number}/"
            f"{EXTRA_FULL_RUNS}...",
            end=" "
        )


        while True:

            try:

                request_start_time = (
                    time.time()
                )


                completion = (
                    client.chat.completions.create(
                        model=MODEL,
                        temperature=0,
                        messages=[
                            {
                                "role":
                                    "system",

                                "content":
                                    promptTemplate
                            },
                            {
                                "role":
                                    "user",

                                "content":
                                    user_content
                            }
                        ]
                    )
                )


                request_end_time = (
                    time.time()
                )

                elapsed_time = (
                    request_end_time
                    - request_start_time
                )


                # ------------------------------------------
                # TOKEN LOG
                # ------------------------------------------

                usage = completion.usage


                with open(
                    TOKEN_LOG_FILE,
                    "a",
                    newline="",
                    encoding="utf-8"
                ) as token_file:

                    writer = csv.writer(
                        token_file
                    )

                    writer.writerow([
                        course_code,
                        stage2_run_number,
                        f"{elapsed_time:.2f}",
                        usage.prompt_tokens,
                        usage.completion_tokens,
                        usage.total_tokens
                    ])


                # ------------------------------------------
                # PARSE RESPONSE
                # ------------------------------------------

                response_text = (
                    completion
                    .choices[0]
                    .message
                    .content
                )


                response_json = json.loads(
                    clean_json(
                        response_text
                    )
                )


                evaluation = response_json[
                    "evaluation"
                ]


                if len(
                    evaluation
                ) != 16:

                    raise ValueError(
                        f"Expected 16 SDGs, "
                        f"received "
                        f"{len(evaluation)}."
                    )


                evaluation_lookup = (
                    evaluation_to_lookup(
                        evaluation
                    )
                )


                # Ensure every requested problematic SDG exists.
                for sdg in problematic_sdgs:

                    if sdg not in (
                        evaluation_lookup
                    ):

                        raise ValueError(
                            f"{sdg} missing from "
                            f"Stage 2 response."
                        )


                raw_full_runs[
                    course_code
                ].append({
                    "stage2_run":
                        stage2_run_number,

                    "evaluation":
                        evaluation
                })


                print(
                    f"{elapsed_time:.2f} sec"
                )

                break


            except Exception as e:

                print(
                    f"\nAPI / parsing error "
                    f"for {course_code}: {e}"
                )

                print(
                    "Retrying in 3 seconds..."
                )

                time.sleep(3)


    # --------------------------------------------------
    # ANALYZE EACH PROBLEMATIC SDG FOR THIS COURSE
    # --------------------------------------------------

    stage2_run_lookups = [
        evaluation_to_lookup(
            run[
                "evaluation"
            ]
        )

        for run in raw_full_runs[
            course_code
        ]
    ]


    for sdg in problematic_sdgs:

        stage1_item = (
            stage1_pair_lookup.get(
                (
                    course_code,
                    sdg
                )
            )
        )


        if stage1_item is None:

            raise ValueError(
                f"Stage 1 unresolved data "
                f"not found for "
                f"{course_code} - {sdg}"
            )


        stage1_scores = [
            int(score)
            for score in stage1_item[
                "stage1_scores"
            ]
        ]

        stage1_categories = [
            get_category(
                score
            )
            for score in stage1_scores
        ]


        stage2_scores = [
            int(
                lookup[
                    sdg
                ]
            )

            for lookup in stage2_run_lookups
        ]

        stage2_categories = [
            get_category(
                score
            )
            for score in stage2_scores
        ]


        combined_scores = (
            stage1_scores
            + stage2_scores
        )

        combined_categories = (
            stage1_categories
            + stage2_categories
        )


        # ----------------------------------------------
        # CATEGORY SUMMARIES
        # ----------------------------------------------

        (
            stage1_dominant,
            stage1_dominant_count,
            stage1_agreement
        ) = dominant_category(
            stage1_categories
        )


        (
            stage2_dominant,
            stage2_dominant_count,
            stage2_agreement
        ) = dominant_category(
            stage2_categories
        )


        (
            combined_dominant,
            combined_dominant_count,
            combined_agreement
        ) = dominant_category(
            combined_categories
        )


        cross_stage_category_distance = (
            category_distance(
                stage1_dominant,
                stage2_dominant
            )
        )


        # ----------------------------------------------
        # CONFIDENCE INTERVAL
        # ----------------------------------------------

        ci = calculate_confidence_interval(
            combined_scores
        )

        category_lower, category_upper = (
            get_category_bounds(
                combined_dominant
            )
        )

        ci_inside_combined_category = (
            ci["ci_lower"] >= category_lower
            and
            ci["ci_upper"] <= category_upper
        )


        # ----------------------------------------------
        # FINAL STATUS
        # ----------------------------------------------

        # The final/provisional category is based on ALL repeated
        # full-context observations, not Stage 2 alone.
        #
        # Example:
        #   inclusive = 4
        #   moderate  = 2
        #   indirect  = 2
        #
        # -> provisional/final category = inclusive
        # -> status = unstable because agreement is only 50%.
        final_category = (
            combined_dominant
        )

        final_score = (
            representative_score_for_category(
                combined_scores,
                final_category
            )
        )

        enough_combined_agreement = (
            combined_agreement
            >= MIN_COMBINED_CATEGORY_AGREEMENT
        )

        stage2_supports_final_category = (
            stage2_dominant
            == combined_dominant
        )

        # IMPORTANT:
        # CI is no longer a hard requirement for stability.
        #
        # A pair is stable_after_recheck when:
        #   - at least 75% of all 8 full-context evaluations agree, AND
        #   - the 3 Stage 2 runs support the same dominant category.
        #
        # CI is retained as uncertainty information only.
        stable_after_recheck = (
            enough_combined_agreement
            and
            stage2_supports_final_category
        )

        if stable_after_recheck:

            status = (
                "stable_after_recheck"
            )

        else:

            status = "unstable"


        # ----------------------------------------------
        # RELIABILITY INTERPRETATION
        # ----------------------------------------------
        #
        # This is descriptive metadata for the user/report.
        # It does not change final_category.
        #
        # HIGH:
        #   category consensus is strong and the CI stays fully
        #   inside the final category.
        #
        # MEDIUM:
        #   category consensus is strong, but the CI crosses a
        #   category boundary. The category is stable, but the
        #   numerical score is boundary-sensitive.
        #
        # LOW:
        #   repeated category evaluations do not meet the Stage 2
        #   stability rule.
        if status == "unstable":

            reliability_level = "low"

        elif ci_inside_combined_category:

            reliability_level = "high"

        else:

            reliability_level = "medium"


        boundary_sensitive = (
            not ci_inside_combined_category
        )


        # ----------------------------------------------
        # RESULT
        # ----------------------------------------------

        result = {
            "course":
                course_code,

            "sdg":
                sdg,

            "stage1_scores":
                stage1_scores,

            "stage1_categories":
                stage1_categories,

            "stage1_dominant_category":
                stage1_dominant,

            "stage1_dominant_count":
                int(
                    stage1_dominant_count
                ),

            "stage1_category_agreement":
                float(
                    stage1_agreement
                ),

            "stage2_scores":
                stage2_scores,

            "stage2_categories":
                stage2_categories,

            "stage2_dominant_category":
                stage2_dominant,

            "stage2_dominant_count":
                int(
                    stage2_dominant_count
                ),

            "stage2_category_agreement":
                float(
                    stage2_agreement
                ),

            "combined_scores":
                combined_scores,

            "combined_categories":
                combined_categories,

            "combined_dominant_category":
                combined_dominant,

            "combined_dominant_count":
                int(
                    combined_dominant_count
                ),

            "combined_category_agreement":
                float(
                    combined_agreement
                ),

            "mean_score":
                float(
                    ci["mean"]
                ),

            "std":
                float(
                    ci["std"]
                )
                if ci["std"] is not None
                else None,

            "ci_95_lower":
                float(
                    ci["ci_lower"]
                )
                if ci["ci_lower"] is not None
                else None,

            "ci_95_upper":
                float(
                    ci["ci_upper"]
                )
                if ci["ci_upper"] is not None
                else None,

            "ci_half_width":
                float(
                    ci["ci_half_width"]
                )
                if ci["ci_half_width"] is not None
                else None,

            "ci_inside_final_category":
                bool(
                    ci_inside_combined_category
                ),

            "boundary_sensitive":
                bool(
                    boundary_sensitive
                ),

            "reliability_level":
                reliability_level,

            "stage2_supports_final_category":
                bool(
                    stage2_supports_final_category
                ),

            "cross_stage_category_distance":
                int(
                    cross_stage_category_distance
                ),

            "status":
                status,

            "final_category":
                final_category,

            "final_score":
                int(
                    final_score
                )
                if final_score is not None
                else None
        }


        results.append(
            result
        )


        print()
        print(
            f"{course_code} - {sdg}"
        )

        print(
            f"  Stage 1: "
            f"{stage1_scores} "
            f"-> {stage1_dominant}"
        )

        print(
            f"  Stage 2: "
            f"{stage2_scores} "
            f"-> {stage2_dominant}"
        )

        print(
            f"  Combined agreement: "
            f"{combined_agreement:.2%}"
        )

        print(
            f"  95% CI: "
            f"[{ci['ci_lower']:.2f}, "
            f"{ci['ci_upper']:.2f}]"
        )

        print(
            f"  CI inside final category: "
            f"{ci_inside_combined_category}"
        )

        print(
            f"  Stage 2 supports final category: "
            f"{stage2_supports_final_category}"
        )

        print(
            f"  Reliability level: "
            f"{reliability_level}"
        )

        print(
            f"  Boundary sensitive: "
            f"{boundary_sensitive}"
        )

        print(
            f"  Status: "
            f"{status}"
        )

        print(
            f"  Final: "
            f"{final_score} "
            f"({final_category})"
        )


    # Save progress after every course.
    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=4,
            ensure_ascii=False
        )


    with open(
        RAW_STAGE2_RUNS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            raw_full_runs,
            file,
            indent=4,
            ensure_ascii=False
        )


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

stable_after_recheck_count = sum(
    1
    for item in results
    if item[
        "status"
    ] == "stable_after_recheck"
)

unstable_count = sum(
    1
    for item in results
    if item[
        "status"
    ] == "unstable"
)


print()
print(
    "========== STAGE 2 SUMMARY =========="
)

print(
    f"Problematic pairs evaluated: "
    f"{len(results)}"
)

print(
    f"Stable after recheck: "
    f"{stable_after_recheck_count}"
)

print(
    f"Unstable: "
    f"{unstable_count}"
)

print()
print(
    f"Results saved to: "
    f"{OUTPUT_FILE}"
)

print(
    f"Raw Stage 2 runs saved to: "
    f"{RAW_STAGE2_RUNS_FILE}"
)

print(
    f"Token usage saved to: "
    f"{TOKEN_LOG_FILE}"
)
