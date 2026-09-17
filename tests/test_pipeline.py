import json

from app.pipeline import run_pipeline


course_data = {
    "courseCode": "MGMT301",
    "courseDescEN": (
      "This course offers a sociological and historical perspective on sustainability that encompasses environmental, economic, and social dimensions, ranging from inequality and poverty to responsible consumption. It introduces key issues, questions, and approaches in contemporary sustainability debates, including the Anthropocene, climate change, circular economy, green transitions, green financing, degrowth, carbon markets, ESG and environmental justice. The course also explores prominent sectors central to public sustainability discourse, such as plastics, fast fashion industry, forests, water and oceans, mining, and electric vehicles. By the end of this course, students will gain a comprehensive understanding of sustainability's historical, social, and political dimensions and its relevance to current environmental and economic challenges. They will develop the ability to analyze sustainability issues across sectors, interpret key concepts like the Anthropocene and circular economy, and critically evaluate regulatory and political approaches. Equipped with sociological and historical frameworks, students will propose practical solutions to enhance sustainability practices in diverse contexts. ",
    ),
    "learningOutcomes":  [
          
        ]
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