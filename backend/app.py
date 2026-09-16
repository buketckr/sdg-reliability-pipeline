import json
import os
import subprocess
import sys

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(
    __file__
).resolve().parent.parent

COURSES_FILE = (
    PROJECT_ROOT
    / "data"
    / "filtered_courses.json"
)

STAGE3_BASE_DIR = (
    PROJECT_ROOT
    / "method_a"
    / "stage3_results"
)


# --------------------------------------------------
# APP
# --------------------------------------------------

app = FastAPI(
    title="SDG Evaluation API"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# REQUEST MODEL
# --------------------------------------------------

class EvaluationRequest(BaseModel):
    courseCode: str


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def load_courses():

    with open(
        COURSES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def find_course(
    course_code
):

    courses = load_courses()

    for course in courses:

        if (
            course.get("courseCode")
            == course_code
        ):

            return course

    return None


def get_next_frontend_run_number():

    run_numbers = []

    if STAGE3_BASE_DIR.exists():

        for item in STAGE3_BASE_DIR.iterdir():

            if (
                item.is_dir()
                and item.name.startswith(
                    "frontend_run"
                )
            ):

                try:
                    number = int(
                        item.name.replace(
                            "frontend_run",
                            ""
                        )
                    )

                    run_numbers.append(
                        number
                    )

                except ValueError:
                    pass

    if not run_numbers:
        return 1

    return max(run_numbers) + 1

def run_python_script(
    script_name,
    env
):

    script_path = (
        PROJECT_ROOT
        / script_name
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script_path)
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"{script_name} failed.\n\n"
            f"STDOUT:\n"
            f"{result.stdout}\n\n"
            f"STDERR:\n"
            f"{result.stderr}"
        )

    return result.stdout


# --------------------------------------------------
# GET COURSES
# --------------------------------------------------

@app.get(
    "/api/courses"
)
def get_courses():

    courses = load_courses()

    return [
        {
            "courseCode":
                course.get(
                    "courseCode"
                ),

            "courseName":
                course.get(
                    "courseName",
                    ""
                ),

            "courseDescEN":
                course.get(
                    "courseDescEN",
                    ""
                ),

            "learningOutcomes":
                course.get(
                    "learningOutcomes",
                    []
                )
        }

        for course in courses
    ]


# --------------------------------------------------
# EVALUATE ONE COURSE
# --------------------------------------------------

@app.post(
    "/api/evaluate"
)
def evaluate_course(
    request: EvaluationRequest
):

    course = find_course(
        request.courseCode
    )

    if course is None:

        raise HTTPException(
            status_code=404,
            detail="Course not found."
        )


    run_number = (
        get_next_frontend_run_number()
    )

    env = os.environ.copy()

    env["RUN"] = str(
        run_number
    )


  

    env["RUN_SOURCE"] = "frontend"

    env["COURSE_CODE"] = (
        request.courseCode
    )


    try:

        # ----------------------------------------------
        # AI
        # Creates the 5 independent evaluations
        # ----------------------------------------------

        ai_output = (
            run_python_script(
                "AI.py",
                env
            )
        )


        # ----------------------------------------------
        # STAGE 1
        # ----------------------------------------------

        stage1_output = (
            run_python_script(
                "stage1_advanced.py",
                env
            )
        )


        # ----------------------------------------------
        # STAGE 2
        # ----------------------------------------------

        stage2_output = (
            run_python_script(
                "stage2_advanced.py",
                env
            )
        )


        # ----------------------------------------------
        # STAGE 3
        # ----------------------------------------------

        stage3_output = (
            run_python_script(
                "stage3_advanced.py",
                env
            )
        )


    except RuntimeError as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    # ----------------------------------------------
    # LOAD FINAL RESULT
    # ----------------------------------------------

    final_file = (
        PROJECT_ROOT
        / "method_a"
        / "stage3_results"
        / f"frontend_run{run_number}"
        / "final_results.json"
    )


    if not final_file.exists():

        raise HTTPException(
            status_code=500,
            detail=(
                "Pipeline completed but "
                "final_results.json was not found."
            )
        )


    with open(
        final_file,
        "r",
        encoding="utf-8"
    ) as file:

        final_results = (
            json.load(file)
        )


    if len(final_results) == 0:

        raise HTTPException(
            status_code=500,
            detail="Final result is empty."
        )


    final_course = (
        final_results[0]
    )


    return {
        "run":
            run_number,

        "course":
            request.courseCode,

        "evaluation":
            final_course[
                "evaluation"
            ],

        "pipeline": {
            "ai":
                "completed",

            "stage1":
                "completed",

            "stage2":
                "completed",

            "stage3":
                "completed"
        }
    }