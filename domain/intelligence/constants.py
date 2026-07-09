"""Episode planning constants."""

MAX_EPISODE_ARTICLES = 8
MAX_EPISODE_MINUTES = 30
MAX_EPISODE_SECONDS = MAX_EPISODE_MINUTES * 60
ESTIMATED_SECONDS_PER_ARTICLE = MAX_EPISODE_SECONDS // MAX_EPISODE_ARTICLES
MIN_KEYWORDS = 1
MAX_KEYWORDS = 3

# Fixed tag taxonomy for the tech podcast. Articles are tagged with 1 to
# MAX_KEYWORDS of these; anything outside the list is discarded so tags stay
# usable for clustering and listener interest matching.
ALLOWED_TAGS: tuple[str, ...] = (
    "Algorithms",
    "LLM",
    "Claude Fable",
    "Machine Learning",
    "Data Science",
    "Infrastructure",
    "Networking",
    "Security",
    "Privacy",
    "UI/UX",
    "Web Development",
    "Mobile",
    "Cloud",
    "DevOps",
    "Databases",
    "Programming Languages",
    "Open Source",
    "Hardware",
    "Robotics",
    "Startups",
)
