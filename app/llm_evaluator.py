import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI
from app.config import (
    MODEL,
    TEMPERATURE,
    INITIAL_RUNS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
)


load_dotenv()


def get_openai_client():

    api_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("API_KEY")
    )

    if not api_key:
        raise ValueError(
            "OpenAI API key was not found. "
            "Set OPENAI_API_KEY or API_KEY in the environment."
        )

    return OpenAI(api_key=api_key)



PROMPT_TEMPLATE = (
    "Evaluate the course description and learning outcomes against "
    "SDG1 through SDG16 in numerical order. Do not evaluate SDG17. "

    "For each SDG, return SDGInfo and correlation. "
    "Use SDGInfo in the format 'SDG<number>'. "
    "Set correlation to an integer from 0 to 100, where higher values "
    "mean stronger correlation and alignment. "

    "Treat evidence as direct only when the course description or "
    "learning outcomes explicitly and substantively address the SDG. "
    "Treat hypothetical applications, transferable skills, general "
    "societal benefits, and downstream effects as indirect evidence. "
    "Do not infer alignment solely from content related to a neighboring "
    "or conceptually similar SDG. "
    "Evidence must specifically support the SDG being evaluated. "

    "Use these scoring categories consistently: "
    "0-19 = no meaningful or only speculative relationship "
    "(0 <= score <= 19). "
    "20-39 = indirect relationship (20 <= score <= 39). "
    "40-69 = moderate relationship; some explicit SDG-related content "
    "is present, but not enough to classify the course as SDG-inclusive "
    "(40 <= score <= 69). "
    "70-89 = SDG-inclusive; the SDG is clearly and substantively "
    "incorporated into the course, but is not its primary focus "
    "(70 <= score <= 89). "
    "90-100 = SDG-focused; the SDG is a central or primary focus "
    "of the course (90 <= score <= 100). "

    "Apply the boundaries exactly: "
    "19 is none/speculative, 20 is indirect, "
    "39 is indirect, 40 is moderate, "
    "69 is moderate, 70 is SDG-inclusive, "
    "89 is SDG-inclusive, and 90 is SDG-focused. "

    "Apply the scoring categories as sequential decision gates. "
    "First determine whether there is explicit SDG-specific evidence "
    "in the course description or learning outcomes. "
    "If there is no explicit SDG-specific evidence, the score must not "
    "exceed 39, even if the course could contribute to the SDG in practice. "

    "If explicit SDG-specific evidence exists, determine whether it is "
    "substantive and integrated into the course. "
    "If the evidence is explicit but limited, peripheral, or only briefly "
    "mentioned, the score must not exceed 69. "
    "Only explicit and substantive SDG-specific evidence may receive "
    "a score of 70 or above. "

    "Finally, determine whether the SDG-related theme characterizes "
    "the course as a whole. "
    "A score of 90 or above may be assigned only when the SDG is a "
    "central or primary focus of the course, rather than one important "
    "topic among several. "

    "Do not classify a relationship as indirect (20-39) when the course "
    "explicitly and substantively addresses content that is part of the SDG. "
    "Do not assign strong relevance based only on indirect evidence. "

    "For SDG4, being a higher-education course is not itself evidence "
    "of alignment. "
    "Assign substantial SDG4 relevance only when the course explicitly "
    "addresses educational quality, access to education, teaching or "
    "learning methods, education policy, educational technologies, "
    "or another substantive aspect of SDG4. "

    "Include every SDG from SDG1 through SDG16. "

    "Return only valid JSON in this format: "
    '{"evaluation":[{"SDGInfo":"SDG1","correlation":0}]}'
)


def clean_json(response_text):


    if not response_text:
        raise ValueError("Model returned an empty response.")

    start = response_text.find("{")
    end = response_text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError(
            "No valid JSON object was found in the model response."
        )

    return response_text[start:end + 1]


def validate_evaluation(evaluation):
 

    if not isinstance(evaluation, list):
        raise ValueError(
            "Model response does not contain a valid 'evaluation' list."
        )

    if len(evaluation) != 16:
        raise ValueError(
            f"Expected 16 SDG evaluations, received {len(evaluation)}."
        )

    validated = []

    for index, item in enumerate(evaluation, start=1):

        if not isinstance(item, dict):
            raise ValueError(
                f"SDG{index} evaluation is not a JSON object."
            )

        expected_sdg = f"SDG{index}"

        sdg_info = item.get("SDGInfo")
        correlation = item.get("correlation")

        if sdg_info != expected_sdg:
            raise ValueError(
                f"Expected {expected_sdg}, received {sdg_info}."
            )

        # Reject booleans because bool is a subclass of int in Python.
        if isinstance(correlation, bool) or not isinstance(correlation, int):
            raise ValueError(
                f"{expected_sdg} correlation must be an integer."
            )

        if correlation < 0 or correlation > 100:
            raise ValueError(
                f"{expected_sdg} correlation must be between 0 and 100."
            )

        validated.append(
            {
                "SDGInfo": expected_sdg,
                "correlation": correlation,
            }
        )

    return validated


def validate_course_data(course_data):

    if not isinstance(course_data, dict):
        raise ValueError("course_data must be a dictionary.")

    course_code = course_data.get("courseCode")

    if not course_code:
        raise ValueError(
            "course_data must contain a non-empty 'courseCode'."
        )

    course_description = (
        course_data.get("courseDescEN")
        or course_data.get("description")
    )

    if not course_description:
        raise ValueError(
            f"Course {course_code} does not contain a course description."
        )

    learning_outcomes = course_data.get(
        "learningOutcomes",
        []
    )

    if learning_outcomes is None:
        learning_outcomes = []

    if not isinstance(learning_outcomes, list):
        raise ValueError(
            "'learningOutcomes' must be a list."
        )

    normalized_outcomes = [
        str(outcome).strip()
        for outcome in learning_outcomes
        if str(outcome).strip()
    ]

    return {
        "courseCode": str(course_code).strip(),
        "courseDescription": str(course_description).strip(),
        "learningOutcomes": normalized_outcomes,
    }



def evaluate_once(
    course_data,
    client=None,
    max_retries=MAX_RETRIES,
):
    
    #Perform one complete SDG1-SDG16 evaluation for one course.
    

    course = validate_course_data(course_data)

    if client is None:
        client = get_openai_client()

    learning_outcomes_text = "\n".join(
        f"- {outcome}"
        for outcome in course["learningOutcomes"]
    )

    if not learning_outcomes_text:
        learning_outcomes_text = "No learning outcomes provided."

    user_message = (
        f"Course Description:\n"
        f"{course['courseDescription']}\n\n"
        f"Learning Outcomes:\n"
        f"{learning_outcomes_text}"
    )

    last_error = None

    for attempt in range(1, max_retries + 1):

        start_time = time.time()

        try:
            completion = client.chat.completions.create(
                model=MODEL,
                temperature=TEMPERATURE,
                messages=[
                    {
                        "role": "system",
                        "content": PROMPT_TEMPLATE,
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
            )

            elapsed_time = time.time() - start_time

            response_text = (
                completion
                .choices[0]
                .message
                .content
            )

            json_text = clean_json(response_text)
            json_data = json.loads(json_text)

            evaluation = validate_evaluation(
                json_data.get("evaluation")
            )

            usage = completion.usage

            return {
                "course": course["courseCode"],
                "evaluation": evaluation,
                "metadata": {
                    "response_time_seconds": round(
                        elapsed_time,
                        3,
                    ),
                    "input_tokens": getattr(
                        usage,
                        "prompt_tokens",
                        None,
                    ),
                    "output_tokens": getattr(
                        usage,
                        "completion_tokens",
                        None,
                    ),
                    "total_tokens": getattr(
                        usage,
                        "total_tokens",
                        None,
                    ),
                },
            }

        except Exception as exc:
            last_error = exc

            if attempt < max_retries:
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Evaluation failed for course "
        f"{course['courseCode']} after "
        f"{max_retries} attempts."
    ) from last_error




def evaluate_course(
    course_data,
    num_runs=INITIAL_RUNS,
):
  
    #Perform multiple independent evaluations of one course.


    if not isinstance(num_runs, int) or num_runs < 1:
        raise ValueError(
            "num_runs must be a positive integer."
        )

    course = validate_course_data(course_data)

    client = get_openai_client()

    runs = []

    for run_number in range(1, num_runs + 1):

        result = evaluate_once(
            course_data=course_data,
            client=client,
        )

        runs.append(
            {
                "run": run_number,
                "evaluation": result["evaluation"],
                "metadata": result["metadata"],
            }
        )

    return {
        "course": course["courseCode"],
        "runs": runs,
    }