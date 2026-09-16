
# MODEL SETTINGS
MODEL = "gpt-5.4"
TEMPERATURE = 0


# PIPELINE RUN COUNTS
INITIAL_RUNS = 5
STAGE2_RUNS = 3
#Caution: Stage 2's current logic is designed around exactly 5+3=8 observations. Therefore xhanging the run counts will require reconsidering the statistical rules.


# STAGE 1 SETTINGS
BOUNDARY_MARGIN = 3


# STAGE 2 SETTINGS
MIN_COMBINED_CATEGORY_AGREEMENT = 0.75


# CATEGORY DEFINITIONS
CATEGORY_ORDER = [
    "none/speculative",
    "indirect",
    "moderate",
    "SDG-inclusive",
    "SDG-focused",
]


CATEGORY_BOUNDS = {
    "none/speculative": (0, 19),
    "indirect": (20, 39),
    "moderate": (40, 69),
    "SDG-inclusive": (70, 89),
    "SDG-focused": (90, 100),
}


# OPENAI / RETRY SETTINGS
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5