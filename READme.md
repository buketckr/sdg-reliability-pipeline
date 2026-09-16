# SDG Reliability Evaluation Pipeline

This project provides a Python-based reliability evaluation pipeline for assessing the relationship between university courses and the United Nations Sustainable Development Goals (SDGs).

The system evaluates SDG1 through SDG16 based on a course description and its learning outcomes. SDG17 is not included.

The project is designed as a framework-independent Python module so that it can be integrated into an existing backend or frontend infrastructure.

---

## Overview

Large Language Model (LLM) evaluations may produce slightly different scores when the same course is evaluated multiple times.

To improve the repeatability of the final SDG classification, this project uses a multi-stage reliability evaluation process.

The complete pipeline is executed through a single function:

```python
from app.pipeline import run_pipeline

result = run_pipeline(course_data)
basman yeterli.
