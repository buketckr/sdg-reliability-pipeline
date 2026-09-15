import json
import os
import time
import math
import csv
from dotenv import load_dotenv
from openai import OpenAI
from scipy import stats
from config import RUN


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------


OUTPUT_DIR = f"method_a/stage2_results/run{RUN}"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

TOKEN_LOG_FILE = f"{OUTPUT_DIR}/token_usage.csv"
UNRESOLVED_FILE = f"method_a/stage1_results/run{RUN}/unresolved_pairs.json"
COURSES_FILE = "data/filtered_courses.json"
OUTPUT_FILE = f"{OUTPUT_DIR}/results.json"

MODEL = "gpt-5.4"

# Stage 2 uses ONLY pair-specific runs for stability / CI.
# Stage 1 scores are kept only for reference.
MIN_PAIR_RUNS = 3
MAX_PAIR_RUNS = 10

# If the first 3 pair-specific runs are all in the same category,
# accept immediately without needing CI escalation.
EARLY_ACCEPT_COUNT = 3

# If early 3/3 agreement is not reached, use these criteria.
MIN_CATEGORY_AGREEMENT = 0.75
MAX_CI_HALF_WIDTH = 5.0


# --------------------------------------------------
# TOKEN LOG
# --------------------------------------------------

with open(
    TOKEN_LOG_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as token_file:

    writer = csv.writer(token_file)

    writer.writerow([
        "course",
        "sdg",
        "pair_run_number",
        "response_time_seconds",
        "input_tokens",
        "output_tokens",
        "total_tokens"
    ])


# --------------------------------------------------
# OPENAI
# --------------------------------------------------

load_dotenv()

client = OpenAI(
    api_key=os.getenv("API_KEY")
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

    raise ValueError(f"Unknown category: {category}")


def calculate_statistics(scores):
    n = len(scores)
    mean_score = sum(scores) / n

    if n < 2:
        return {
            "n": n,
            "mean": mean_score,
            "std": None,
            "ci_lower": None,
            "ci_upper": None,
            "ci_half_width": None
        }

    std = float(stats.tstd(scores))

    # If every score is exactly the same, CI collapses to the mean.
    if std == 0:
        return {
            "n": n,
            "mean": mean_score,
            "std": 0.0,
            "ci_lower": mean_score,
            "ci_upper": mean_score,
            "ci_half_width": 0.0
        }

    standard_error = std / math.sqrt(n)

    t_critical = float(
        stats.t.ppf(
            0.975,
            df=n - 1
        )
    )

    margin = t_critical * standard_error

    return {
        "n": n,
        "mean": mean_score,
        "std": std,
        "ci_lower": mean_score - margin,
        "ci_upper": mean_score + margin,
        "ci_half_width": margin
    }


def category_information(scores):
    categories = [
        get_category(score)
        for score in scores
    ]

    counts = {}

    for category in categories:
        counts[category] = counts.get(category, 0) + 1

    dominant_category = max(
        counts,
        key=counts.get
    )

    dominant_count = counts[
        dominant_category
    ]

    agreement = (
        dominant_count
        / len(categories)
    )

    return {
        "categories": categories,
        "category_counts": counts,
        "dominant_category": dominant_category,
        "dominant_count": dominant_count,
        "agreement": agreement
    }


def evaluate_pair_status(scores):
    """
    Stage 2 decision logic:

    1) Fewer than 3 pair-specific runs:
       keep running.

    2) Exactly/at least 3 runs and all first/current runs agree in category:
       accept immediately.

    3) Otherwise:
       use category agreement + 95% CI.
       CI must lie fully inside the dominant category and be sufficiently narrow.

    Returns:
        stable (bool)
        diagnostic (dict)
        stop_reason (str or None)
    """

    if len(scores) < MIN_PAIR_RUNS:
        return False, None, None

    category_info = category_information(scores)

    # Early stop: all pair-specific runs so far agree in category.
    # At n=3 this implements the intended 3/3 rule.
    if (
        len(scores) == MIN_PAIR_RUNS
        and category_info["dominant_count"] == EARLY_ACCEPT_COUNT
    ):
        statistics = calculate_statistics(scores)

        diagnostic = {
            **statistics,
            **category_info,
            "ci_inside_category": True,
            "ci_narrow_enough": (
                statistics["ci_half_width"] is not None
                and statistics["ci_half_width"] <= MAX_CI_HALF_WIDTH
            ),
            "stable": True
        }

        return True, diagnostic, "3/3 pair-specific category agreement"

    statistics = calculate_statistics(scores)

    dominant_category = category_info[
        "dominant_category"
    ]

    lower_bound, upper_bound = (
        get_category_bounds(
            dominant_category
        )
    )

    ci_inside_category = (
        statistics["ci_lower"] >= lower_bound
        and
        statistics["ci_upper"] <= upper_bound
    )

    enough_category_agreement = (
        category_info["agreement"]
        >= MIN_CATEGORY_AGREEMENT
    )

    ci_narrow_enough = (
        statistics["ci_half_width"]
        <= MAX_CI_HALF_WIDTH
    )

    stable = (
        ci_inside_category
        and
        enough_category_agreement
        and
        ci_narrow_enough
    )

    diagnostic = {
        **statistics,
        **category_info,
        "ci_inside_category": bool(ci_inside_category),
        "ci_narrow_enough": bool(ci_narrow_enough),
        "stable": bool(stable)
    }

    stop_reason = (
        "CI + category agreement criteria reached"
        if stable
        else None
    )

    return bool(stable), diagnostic, stop_reason


# --------------------------------------------------
# PAIR-SPECIFIC PROMPT
# --------------------------------------------------

pair_prompt = (
    "Evaluate the provided university course only against the specified SDG. "

    "Return SDGInfo and correlation. "
    "Use SDGInfo in the format 'SDG<number>'. "
    "Set correlation to an integer from 0 to 100, where higher values mean stronger correlation and alignment. "

    "Treat evidence as direct only when the course description or learning outcomes explicitly and substantively address the specified SDG. "
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

    "Do not classify a relationship as indirect (21-40) when the course explicitly and substantively addresses content that is part of the specified SDG. "
    "Do not assign strong relevance based only on indirect evidence. "

    "For SDG4, being a higher-education course is not itself evidence of alignment. "
    "Assign substantial SDG4 relevance only when the course explicitly addresses educational quality, access to education, teaching or learning methods, education policy, educational technologies, or another substantive aspect of SDG4. "

    "Evaluate only the specified SDG and do not add any other SDGs. "

    "Return only valid JSON in this format: "
    '{"SDGInfo":"SDG10","correlation":65}'
)


# --------------------------------------------------
# LOAD UNRESOLVED PAIRS
# --------------------------------------------------

with open(
    UNRESOLVED_FILE,
    "r",
    encoding="utf-8"
) as file:

    unresolved_pairs = json.load(file)


# --------------------------------------------------
# LOAD COURSE INFORMATION
# --------------------------------------------------

with open(
    COURSES_FILE,
    "r",
    encoding="utf-8"
) as file:

    course_catalog = json.load(file)


course_lookup = {
    course["courseCode"]: course
    for course in course_catalog
}


# --------------------------------------------------
# PROCESS EACH UNRESOLVED PAIR
# --------------------------------------------------

results = []


for pair_index, pair in enumerate(
    unresolved_pairs,
    start=1
):

    course_code = pair["course"]
    sdg = pair["sdg"]

    print()
    print(
        f"Pair {pair_index}/{len(unresolved_pairs)}: "
        f"{course_code} - {sdg}"
    )

    course = course_lookup.get(
        course_code
    )

    if course is None:
        print(
            f"ERROR: {course_code} not found."
        )
        continue


    course_description = course.get(
        "courseDescEN",
        ""
    )

    learning_outcomes = "\n".join(
        course.get(
            "learningOutcomes",
            []
        )
    )


    # Stage 1 scores are kept only as reference.
    # They are NOT included in Stage 2 CI/statistics because
    # Stage 2 uses a different pair-specific evaluation context.
    stage1_scores = [
        int(score)
        for score in pair["existing_scores"]
    ]

    stage1_categories = [
        get_category(score)
        for score in stage1_scores
    ]

    print(
        f"Stage 1 scores (reference only): "
        f"{stage1_scores}"
    )

    # IMPORTANT:
    # Stage 2 starts a fresh, independent pair-specific sample.
    pair_scores = []

    stop_reason = None


    # --------------------------------------------------
    # ADD PAIR-SPECIFIC RUNS
    # --------------------------------------------------

    while len(pair_scores) < MAX_PAIR_RUNS:

        stable, diagnostic, stop_reason = (
            evaluate_pair_status(
                pair_scores
            )
        )

        if stable:
            print(
                f"Stopping criteria reached: "
                f"{stop_reason}"
            )
            break


        user_content = (
            f"Course: {course_code}\n"
            f"SDG to evaluate: {sdg}\n\n"

            f"Course Description:\n"
            f"{course_description}\n\n"

            f"Learning Outcomes:\n"
            f"{learning_outcomes}"
        )


        try:
            request_start_time = time.time()

            completion = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": pair_prompt
                    },
                    {
                        "role": "user",
                        "content": user_content
                    }
                ]
            )

            request_end_time = time.time()
            elapsed_time = (
                request_end_time
                - request_start_time
            )

            usage = completion.usage

            # Log billed token usage immediately after the API response.
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
                    sdg,
                    len(pair_scores) + 1,
                    f"{elapsed_time:.2f}",
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens
                ])


            response_text = (
                completion
                .choices[0]
                .message
                .content
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


            response_json = json.loads(
                response_text
            )


            new_score = int(
                response_json[
                    "correlation"
                ]
            )


            pair_scores.append(
                new_score
            )


            print(
                f"Pair run {len(pair_scores)}: "
                f"{new_score} "
                f"({get_category(new_score)})"
            )


        except Exception as e:
            print(
                f"API / parsing error: {e}"
            )

            time.sleep(3)
            continue


    # --------------------------------------------------
    # FINAL STAGE 2 STATISTICS
    # --------------------------------------------------

    statistics = calculate_statistics(
        pair_scores
    )

    category_info = category_information(
        pair_scores
    )


    dominant_category = (
        category_info[
            "dominant_category"
        ]
    )

    category_lower, category_upper = (
        get_category_bounds(
            dominant_category
        )
    )


    ci_inside_category = (
        statistics["ci_lower"]
        >= category_lower
        and
        statistics["ci_upper"]
        <= category_upper
    )


    # Re-evaluate final status after leaving the loop.
    final_stable, final_diagnostic, final_stop_reason = (
        evaluate_pair_status(
            pair_scores
        )
    )

    if (
        not final_stable
        and len(pair_scores) >= MAX_PAIR_RUNS
    ):
        final_stop_reason = (
            "maximum pair-specific runs reached"
        )


    result = {
        "course": course_code,
        "sdg": sdg,

        # Stage 1 information retained for traceability only.
        "stage1_scores": stage1_scores,
        "stage1_categories": stage1_categories,

        # Stage 2 sample used for all reliability statistics.
        "pair_specific_scores": [
            int(score)
            for score in pair_scores
        ],

        "pair_specific_total_runs":
            int(len(pair_scores)),

        "pair_specific_categories":
            category_info[
                "categories"
            ],

        "category_counts": {
            key: int(value)
            for key, value
            in category_info[
                "category_counts"
            ].items()
        },

        "dominant_category":
            dominant_category,

        "category_agreement":
            float(
                category_info[
                    "agreement"
                ]
            ),

        "mean_score":
            float(
                statistics[
                    "mean"
                ]
            ),

        "std":
            float(
                statistics[
                    "std"
                ]
            ),

        "ci_95_lower":
            float(
                statistics[
                    "ci_lower"
                ]
            ),

        "ci_95_upper":
            float(
                statistics[
                    "ci_upper"
                ]
            ),

        "ci_half_width":
            float(
                statistics[
                    "ci_half_width"
                ]
            ),

        "ci_inside_dominant_category":
            bool(
                ci_inside_category
            ),

        "stable":
            bool(
                final_stable
            ),

        "stop_reason":
            final_stop_reason
    }


    results.append(
        result
    )


    print()
    print(
        f"Stage 2 dominant category: "
        f"{dominant_category}"
    )

    print(
        f"Stage 2 category agreement: "
        f"{category_info['agreement']:.2%}"
    )

    print(
        f"Stage 2 mean: "
        f"{statistics['mean']:.2f}"
    )

    print(
        f"Stage 2 95% CI: "
        f"[{statistics['ci_lower']:.2f}, "
        f"{statistics['ci_upper']:.2f}]"
    )

    print(
        f"Stage 2 stable: "
        f"{final_stable}"
    )

    print(
        f"Stop reason: "
        f"{final_stop_reason}"
    )


    # Save after every pair
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


print()
print(
    f"Finished. Results saved to "
    f"{OUTPUT_FILE}"
)

print(
    f"Token usage saved to "
    f"{TOKEN_LOG_FILE}"
)
