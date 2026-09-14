# This version performs 5 independent full evaluation runs.
# Each run processes all selected courses and saves a separate JSON file.

from dotenv import load_dotenv
from openai import OpenAI
import json
import time
import os
import csv

from config import RUN


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

MODEL = "gpt-5.4"

NUM_INTERNAL_RUNS = 5

INPUT_FILE = "filtered_courses.json"

OUTPUT_DIR = f"method_a/runs/run{RUN}"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# --------------------------------------------------
# OPENAI
# --------------------------------------------------

load_dotenv()

API_KEY = os.getenv("API_KEY")

client = OpenAI(
    api_key=API_KEY
)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def save_progress(
    json_data,
    json_filepath,
    error_array
):
    try:
        with open(
            json_filepath,
            "w",
            encoding="utf-8"
        ) as json_file:

            json.dump(
                json_data,
                json_file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as e:
        print(
            f"Failed to save JSON progress: {e}"
        )

    print(
        f"Errors so far: {error_array}"
    )


def clean_json(response_text):

    start = response_text.find("{")
    end = response_text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "No JSON object found in model response."
        )

    return response_text[
        start:end + 1
    ]


# --------------------------------------------------
# LOAD COURSES
# --------------------------------------------------

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as file:

    course_catalog = json.load(file)


# For the current experiment, use first 9 courses.
course_catalog = course_catalog[:9]

course_count = len(
    course_catalog
)


# --------------------------------------------------
# PROMPT
# --------------------------------------------------

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
# PERFORM 5 FULL INDEPENDENT RUNS
# --------------------------------------------------

overall_start_time = time.time()


for internal_run in range(
    1,
    NUM_INTERNAL_RUNS + 1
):

    print()
    print(
        "=" * 60
    )

    print(
        f"STARTING FULL RUN "
        f"{internal_run}/{NUM_INTERNAL_RUNS}"
    )

    print(
        "=" * 60
    )


    # --------------------------------------------------
    # OUTPUT FILES FOR THIS RUN
    # --------------------------------------------------

    output_file_path = (
        f"{OUTPUT_DIR}/"
        f"run{internal_run}.json"
    )

    token_log_file = (
        f"{OUTPUT_DIR}/"
        f"run{internal_run}_token_usage.csv"
    )


    # --------------------------------------------------
    # RESET VARIABLES FOR THIS RUN
    # --------------------------------------------------

    idx = 0

    json_array = []

    error_array = []

    empty_array = []

    error_counter = 0


    # --------------------------------------------------
    # CREATE TOKEN LOG
    # --------------------------------------------------

    with open(
        token_log_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as token_file:

        writer = csv.writer(
            token_file
        )

        writer.writerow([
            "courseCode",
            "response_time_seconds",
            "input_tokens",
            "output_tokens",
            "total_tokens"
        ])


    run_start_time = time.time()


    # --------------------------------------------------
    # PROCESS ALL COURSES
    # --------------------------------------------------

    while idx < course_count:

        course = course_catalog[
            idx
        ]


        course_desc = course[
            "courseDescEN"
        ]

        course_code = course[
            "courseCode"
        ]


        # --------------------------------------------------
        # EMPTY DESCRIPTION
        # --------------------------------------------------

        if (
            course_desc == ""
            or course_desc is None
        ):

            empty_array.append(
                course_code
            )

            idx += 1

            continue


        learning_outcomes = " ".join(
            course.get(
                "learningOutcomes",
                []
            )
        )


        print(
            f"Run {internal_run} | "
            f"({idx + 1}/{course_count}) "
            f"{course_code}",
            end=" "
        )


        completion = None

        request_start_time = (
            time.time()
        )


        # --------------------------------------------------
        # API CALL
        # --------------------------------------------------

        try:

            completion = (
                client.chat.completions.create(
                    model=MODEL,
                    temperature=0,
                    messages=[
                        {
                            "role": "system",
                            "content":
                                promptTemplate
                        },
                        {
                            "role": "user",
                            "content":
                                (
                                    f"Course Description: "
                                    f"{course_desc}\n\n"
                                    f"Learning Outcomes: "
                                    f"{learning_outcomes}"
                                )
                        }
                    ]
                )
            )


        except Exception as e:

            print(
                f"\nAPI error for "
                f"{course_code}: {e}"
            )

            time.sleep(5)

            save_progress(
                json_array,
                output_file_path,
                error_array
            )

            continue


        request_end_time = (
            time.time()
        )

        elapsed_time = (
            request_end_time
            - request_start_time
        )


        # --------------------------------------------------
        # TOKEN LOG
        # --------------------------------------------------

        usage = completion.usage


        with open(
            token_log_file,
            "a",
            newline="",
            encoding="utf-8"
        ) as token_file:

            writer = csv.writer(
                token_file
            )

            writer.writerow([
                course_code,
                f"{elapsed_time:.2f}",
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens
            ])


        # --------------------------------------------------
        # PARSE RESPONSE
        # --------------------------------------------------

        try:

            json_content = (
                completion
                .choices[0]
                .message
                .content
            )


            json_content = (
                clean_json(
                    json_content
                )
            )


            json_content = (
                json_content
                .replace(
                    "```json",
                    ""
                )
                .replace(
                    "```",
                    ""
                )
            )


            json_data = json.loads(
                json_content
            )


            obj = {
                "course":
                    course_code,

                "evaluation":
                    json_data[
                        "evaluation"
                    ]
            }


            json_array.append(
                obj
            )


            idx += 1

            error_counter = 0


            print(
                f"- "
                f"{elapsed_time:.2f} sec"
            )


            # Save after each successful course.
            save_progress(
                json_array,
                output_file_path,
                error_array
            )


        except Exception as e:

            error_counter += 1


            print(
                f"\nJSON processing error "
                f"for {course_code}: {e}"
            )


            if error_counter >= 2:

                error_array.append(
                    course_code
                )

                idx += 1

                error_counter = 0


                print(
                    f"Skipping "
                    f"{course_code}"
                )


    # --------------------------------------------------
    # SAVE COMPLETED RUN
    # --------------------------------------------------

    save_progress(
        json_array,
        output_file_path,
        error_array
    )


    run_end_time = time.time()

    run_duration = (
        run_end_time
        - run_start_time
    )


    print()
    print(
        f"Run {internal_run} completed."
    )

    print(
        f"Time: "
        f"{run_duration:.2f} seconds"
    )

    print(
        f"Results: "
        f"{output_file_path}"
    )

    print(
        f"Token usage: "
        f"{token_log_file}"
    )


    # --------------------------------------------------
    # OPTIONAL ERROR LOGS
    # --------------------------------------------------

    if error_array:

        error_file = (
            f"{OUTPUT_DIR}/"
            f"run{internal_run}_errors.txt"
        )

        with open(
            error_file,
            "w",
            encoding="utf-8"
        ) as text_file:

            for course_code in error_array:

                text_file.write(
                    course_code + "\n"
                )


    if empty_array:

        empty_file = (
            f"{OUTPUT_DIR}/"
            f"run{internal_run}_empty_courses.txt"
        )

        with open(
            empty_file,
            "w",
            encoding="utf-8"
        ) as text_file:

            for course_code in empty_array:

                text_file.write(
                    course_code + "\n"
                )


# --------------------------------------------------
# FINISHED
# --------------------------------------------------

overall_end_time = time.time()

overall_duration = (
    overall_end_time
    - overall_start_time
)


print()
print(
    "=" * 60
)

print(
    "ALL 5 RUNS COMPLETED"
)

print(
    "=" * 60
)

print(
    f"Total time: "
    f"{overall_duration:.2f} seconds"
)

print(
    f"Output directory: "
    f"{OUTPUT_DIR}"
)