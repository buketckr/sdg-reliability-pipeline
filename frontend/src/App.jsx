import { useEffect, useState } from "react";

function App() {
  const API_BASE = "http://localhost:8000";

  const [courses, setCourses] = useState([]);
  const [selectedCourseCode, setSelectedCourseCode] = useState("");
  const [selectedCourse, setSelectedCourse] = useState(null);

  const [evaluation, setEvaluation] = useState([]);

  const [loadingCourses, setLoadingCourses] = useState(true);
  const [evaluating, setEvaluating] = useState(false);

  const [error, setError] = useState("");
  const [runNumber, setRunNumber] = useState(null);

  // --------------------------------------------------
  // LOAD COURSES
  // --------------------------------------------------

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoadingCourses(true);
        setError("");

        const response = await fetch(
          `${API_BASE}/api/courses`
        );

        if (!response.ok) {
          throw new Error(
            "Failed to fetch courses."
          );
        }

        const data = await response.json();

        setCourses(data);

        if (data.length > 0) {
          setSelectedCourseCode(
            data[0].courseCode
          );

          setSelectedCourse(
            data[0]
          );
        }
      } catch (err) {
        setError(
          err.message
        );
      } finally {
        setLoadingCourses(false);
      }
    };

    fetchCourses();
  }, []);

  // --------------------------------------------------
  // COURSE CHANGE
  // --------------------------------------------------

  const handleCourseChange = (
    event
  ) => {
    const courseCode =
      event.target.value;

    setSelectedCourseCode(
      courseCode
    );

    setEvaluation([]);
    setRunNumber(null);
    setError("");

    const course =
      courses.find(
        (item) =>
          item.courseCode ===
          courseCode
      );

    setSelectedCourse(
      course || null
    );
  };

  // --------------------------------------------------
  // RUN FULL PIPELINE
  // AI -> STAGE 1 -> STAGE 2 -> STAGE 3
  // --------------------------------------------------

  const handleEvaluate = async () => {
    if (!selectedCourseCode) {
      return;
    }

    try {
      setEvaluating(true);
      setError("");
      setEvaluation([]);
      setRunNumber(null);

      const response = await fetch(
        `${API_BASE}/api/evaluate`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            courseCode:
              selectedCourseCode,
          }),
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Evaluation failed."
        );
      }

      setEvaluation(
        data.evaluation || []
      );

      setRunNumber(
        data.run ?? null
      );
    } catch (err) {
      setError(
        err.message
      );
    } finally {
      setEvaluating(false);
    }
  };

  // --------------------------------------------------
  // DISPLAY HELPERS
  // --------------------------------------------------

  const formatStatus = (
    status
  ) => {
    if (!status) {
      return "-";
    }

    return status
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) =>
        letter.toUpperCase()
      );
  };

  const formatReliability = (
    item
  ) => {
    const level =
      item.reliability
        ?.reliability_level;

    if (level) {
      return level.toUpperCase();
    }

    if (
      item.status === "stable"
    ) {
      return "HIGH";
    }

    if (
      item.status ===
      "borderline"
    ) {
      return "MEDIUM";
    }

    if (
      item.status ===
      "low_relevance_variation"
    ) {
      return "MEDIUM";
    }

    return "-";
  };

  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <header style={styles.header}>
          <h1 style={styles.title}>
            SDG Course Evaluation
          </h1>

          <p style={styles.subtitle}>
            Select a course and run the
            complete reliability pipeline
            against SDG1 through SDG16.
          </p>
        </header>

        {error && (
          <div style={styles.errorBox}>
            {error}
          </div>
        )}

        {loadingCourses ? (
          <div style={styles.card}>
            <p>
              Loading courses...
            </p>
          </div>
        ) : (
          <>
            <div style={styles.card}>
              <div
                style={
                  styles.formGroup
                }
              >
                <label
                  htmlFor="course"
                  style={styles.label}
                >
                  Select Course
                </label>

                <select
                  id="course"
                  value={
                    selectedCourseCode
                  }
                  onChange={
                    handleCourseChange
                  }
                  style={styles.select}
                  disabled={evaluating}
                >
                  {courses.map(
                    (course) => (
                      <option
                        key={
                          course.courseCode
                        }
                        value={
                          course.courseCode
                        }
                      >
                        {
                          course.courseCode
                        }
                        {course.courseName
                          ? ` - ${course.courseName}`
                          : ""}
                      </option>
                    )
                  )}
                </select>
              </div>
            </div>

            {selectedCourse && (
              <div
                style={styles.card}
              >
                <div
                  style={
                    styles.courseHeader
                  }
                >
                  <div>
                    <h2
                      style={{
                        marginTop: 0,
                        marginBottom:
                          "4px",
                      }}
                    >
                      {
                        selectedCourse.courseCode
                      }
                    </h2>

                    {selectedCourse.courseName && (
                      <p
                        style={
                          styles.courseName
                        }
                      >
                        {
                          selectedCourse.courseName
                        }
                      </p>
                    )}
                  </div>
                </div>

                <div
                  style={
                    styles.section
                  }
                >
                  <h3>
                    Course Description
                  </h3>

                  <p
                    style={
                      styles.text
                    }
                  >
                    {selectedCourse.courseDescEN ||
                      "No description available."}
                  </p>
                </div>

                <div
                  style={
                    styles.section
                  }
                >
                  <h3>
                    Learning Outcomes
                  </h3>

                  {selectedCourse
                    .learningOutcomes
                    ?.length > 0 ? (
                    <ul>
                      {selectedCourse.learningOutcomes.map(
                        (
                          outcome,
                          index
                        ) => (
                          <li
                            key={
                              index
                            }
                            style={{
                              marginBottom:
                                "8px",
                            }}
                          >
                            {
                              outcome
                            }
                          </li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p>
                      No learning
                      outcomes available.
                    </p>
                  )}
                </div>

                <button
                  onClick={
                    handleEvaluate
                  }
                  disabled={
                    evaluating
                  }
                  style={{
                    ...styles.button,

                    opacity:
                      evaluating
                        ? 0.7
                        : 1,

                    cursor:
                      evaluating
                        ? "not-allowed"
                        : "pointer",
                  }}
                >
                  {evaluating
                    ? "Running Reliability Pipeline..."
                    : "Evaluate Course"}
                </button>

                {evaluating && (
                  <p
                    style={
                      styles.loadingText
                    }
                  >
                    Running AI
                    evaluations, Stage
                    1, Stage 2 if
                    required, and Stage
                    3...
                  </p>
                )}
              </div>
            )}
          </>
        )}

        {evaluation.length > 0 && (
          <div style={styles.card}>
            <div
              style={
                styles.resultsHeader
              }
            >
              <div>
                <h2
                  style={{
                    marginTop: 0,
                    marginBottom:
                      "4px",
                  }}
                >
                  Final Evaluation
                  Results
                </h2>

                <p
                  style={{
                    margin: 0,
                  }}
                >
                  Course:{" "}
                  <strong>
                    {
                      selectedCourseCode
                    }
                  </strong>
                </p>
              </div>

              {runNumber !== null && (
                <div
                  style={
                    styles.runBadge
                  }
                >
                  Run {runNumber}
                </div>
              )}
            </div>

            <div
              style={
                styles.tableWrapper
              }
            >
              <table
                style={
                  styles.table
                }
              >
                <thead>
                  <tr>
                    <th
                      style={
                        styles.th
                      }
                    >
                      SDG
                    </th>

                    <th
                      style={
                        styles.th
                      }
                    >
                      Score
                    </th>

                    <th
                      style={
                        styles.th
                      }
                    >
                      Category
                    </th>

                    <th
                      style={
                        styles.th
                      }
                    >
                      Status
                    </th>

                    <th
                      style={
                        styles.th
                      }
                    >
                      Reliability
                    </th>

                    <th
                      style={
                        styles.th
                      }
                    >
                      Source
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {evaluation.map(
                    (item) => (
                      <tr
                        key={
                          item.SDGInfo
                        }
                      >
                        <td
                          style={
                            styles.td
                          }
                        >
                          <strong>
                            {
                              item.SDGInfo
                            }
                          </strong>
                        </td>

                        <td
                          style={
                            styles.td
                          }
                        >
                          {
                            item.correlation
                          }
                        </td>

                        <td
                          style={
                            styles.td
                          }
                        >
                          {
                            item.category
                          }
                        </td>

                        <td
                          style={
                            styles.td
                          }
                        >
                          {formatStatus(
                            item.status
                          )}
                        </td>

                        <td
                          style={
                            styles.td
                          }
                        >
                          {formatReliability(
                            item
                          )}
                        </td>

                        <td
                          style={
                            styles.td
                          }
                        >
                          {item.source ||
                            "-"}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#f5f6f8",
    padding: "32px 16px",
    fontFamily:
      "Arial, Helvetica, sans-serif",
    color: "#222",
  },

  container: {
    maxWidth: "1200px",
    margin: "0 auto",
  },

  header: {
    marginBottom: "24px",
  },

  title: {
    marginBottom: "8px",
  },

  subtitle: {
    marginTop: 0,
    color: "#666",
  },

  card: {
    background: "#ffffff",
    border: "1px solid #ddd",
    borderRadius: "10px",
    padding: "24px",
    marginBottom: "24px",
  },

  errorBox: {
    background: "#ffe8e8",
    border: "1px solid #f1b5b5",
    padding: "14px",
    borderRadius: "8px",
    marginBottom: "20px",
  },

  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },

  label: {
    fontWeight: "bold",
  },

  select: {
    padding: "12px",
    fontSize: "16px",
    borderRadius: "6px",
    border: "1px solid #bbb",
  },

  courseHeader: {
    display: "flex",
    justifyContent:
      "space-between",
    alignItems: "center",
  },

  courseName: {
    marginTop: 0,
    color: "#666",
  },

  section: {
    marginTop: "24px",
  },

  text: {
    lineHeight: 1.6,
  },

  button: {
    marginTop: "20px",
    padding: "12px 20px",
    border: "none",
    borderRadius: "6px",
    background: "#222",
    color: "#fff",
    fontSize: "16px",
    fontWeight: "bold",
  },

  loadingText: {
    marginTop: "12px",
    color: "#666",
  },

  resultsHeader: {
    display: "flex",
    justifyContent:
      "space-between",
    alignItems: "center",
    marginBottom: "20px",
  },

  runBadge: {
    padding: "8px 12px",
    background: "#eee",
    borderRadius: "6px",
    fontWeight: "bold",
  },

  tableWrapper: {
    overflowX: "auto",
  },

  table: {
    width: "100%",
    borderCollapse: "collapse",
  },

  th: {
    border: "1px solid #ddd",
    padding: "12px",
    textAlign: "left",
    background: "#f3f3f3",
    whiteSpace: "nowrap",
  },

  td: {
    border: "1px solid #ddd",
    padding: "12px",
    textAlign: "left",
    verticalAlign: "top",
  },
};

export default App;