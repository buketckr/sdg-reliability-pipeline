import json

from app.pipeline import run_pipeline


course_data = {
    "courseCode": "SPS374",
    "courseDescEN": (
        "This course aims to provide an introduction to the global environmental challenges with their scientific, economic and political aspects from an interdisciplinary natural and social science perspective. This course equips students with skills to comprehend and analyses the historical background, as well as the future outlook of current environmental problems caused by the immense impact of human civilizations, particularly by economic growth and changing production-consumption patterns. Topics to be discussed include environmental pollution and ecological footprint, global issues such as ozone depletion, deforestation, climate change, and biodiversity loss, air pollution and other environmental health issues, urban environmental problems, food and water politics, plastic pollution and the oceans. Course include discussions of case studies for the solutions and movements for a sustainable future, such as eco-innovation, green economy, and environmentalist campaigns. ",
    ),
    "learningOutcomes": []
}


result = run_pipeline(course_data)


print(
    json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    )
)


with open(
    "test_result.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        result,
        file,
        indent=4,
        ensure_ascii=False
    )


print("\nPipeline completed successfully.")
print("Result saved to test_result.json")