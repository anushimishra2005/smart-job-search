import re

from skill_extractor import extract_skills


# Common experience-level phrases
EXPERIENCE_PATTERNS = {
    "entry-level": [
        r"\bentry[- ]level\b",
        r"\bentry level\b",
        r"\bfresher\b",
        r"\bfreshers\b",
        r"\bgraduate\b",
        r"\bnew grad\b",
        r"\b0[- ]?2 years?\b",
    ],
    "junior": [
        r"\bjunior\b",
        r"\bjunior[- ]level\b",
        r"\b0[- ]?1 years?\b",
        r"\b1[- ]?2 years?\b",
    ],
    "mid-level": [
        r"\bmid[- ]level\b",
        r"\bmid level\b",
        r"\b2[- ]?5 years?\b",
        r"\b3[- ]?5 years?\b",
    ],
    "senior": [
        r"\bsenior\b",
        r"\bsenior[- ]level\b",
        r"\b5\+ years?\b",
        r"\b5 or more years?\b",
        r"\b6\+ years?\b",
    ],
}


# Common location patterns.
# This is intentionally limited to common Indian job-search locations.
LOCATIONS = [
    "Bangalore",
    "Bengaluru",
    "Hyderabad",
    "Pune",
    "Mumbai",
    "Delhi",
    "Delhi NCR",
    "Noida",
    "Gurgaon",
    "Gurugram",
    "Chennai",
    "Kolkata",
    "Ahmedabad",
    "Jaipur",
    "Chandigarh",
    "Kochi",
    "Thiruvananthapuram",
    "Indore",
    "India",
    "Remote",
]


JOB_TITLE_PATTERNS = [
    "software developer",
    "software engineer",
    "full stack developer",
    "full-stack developer",
    "frontend developer",
    "front-end developer",
    "backend developer",
    "back-end developer",
    "web developer",
    "mobile developer",
    "android developer",
    "ios developer",
    "python developer",
    "java developer",
    "data scientist",
    "data analyst",
    "data engineer",
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "devops engineer",
    "cloud engineer",
    "qa engineer",
    "test engineer",
    "application developer",
    "graduate engineer trainee",
]


def _find_location(query):
    """Find a known location in the natural-language query."""

    query_lower = query.lower()

    # Longest names first so 'Delhi NCR' wins over 'Delhi'.
    sorted_locations = sorted(
        LOCATIONS,
        key=len,
        reverse=True
    )

    for location in sorted_locations:
        if re.search(
            rf"\b{re.escape(location.lower())}\b",
            query_lower
        ):
            return location

    return "India"


def _find_experience_level(query):
    """Find the requested experience level."""

    for level, patterns in EXPERIENCE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return level

    return None


def _find_job_title(query):
    """Find the most relevant job title in the query."""

    query_lower = query.lower()

    sorted_titles = sorted(
        JOB_TITLE_PATTERNS,
        key=len,
        reverse=True
    )

    # First try exact multi-word job titles.
    for title in sorted_titles:
        if re.search(
            rf"\b{re.escape(title)}\b",
            query_lower
        ):
            return title.replace("-", " ").title()

    # Generic fallback for phrases such as:
    # "Python developer"
    # "Java developer"
    # "React developer"
    match = re.search(
        r"\b([a-zA-Z+#.]+)\s+(developer|engineer|analyst|scientist)\b",
        query,
        re.IGNORECASE
    )

    if match:
        return f"{match.group(1)} {match.group(2)}".title()

    return None

def _find_recency(query):
    """Detect how recently a job should have been posted."""

    query_lower = query.lower()

    if re.search(r"\btoday\b", query_lower):
        return 1

    if re.search(r"\byesterday\b", query_lower):
        return 2

    match = re.search(
        r"(?:last|past|previous)\s+(\d+)\s+days?",
        query_lower
    )

    if match:
        return int(match.group(1))

    match = re.search(
        r"(?:last|past|previous)\s+(\d+)\s+weeks?",
        query_lower
    )

    if match:
        return int(match.group(1)) * 7

    match = re.search(
        r"(?:last|past|previous)\s+(\d+)\s+months?",
        query_lower
    )

    if match:
        return int(match.group(1)) * 30

    if any(
        phrase in query_lower
        for phrase in [
            "recent",
            "recently",
            "this week",
            "past week",
            "last week",
        ]
    ):
        return 7

    if any(
        phrase in query_lower
        for phrase in [
            "this month",
            "last month",
            "past month",
        ]
    ):
        return 30

    return 30

def _clean_search_keywords(query):
    """
    Remove natural-language filter words, locations, experience
    phrases and recency expressions from the query.
    """

    text = query.lower()

    # Remove known locations.
    for location in sorted(LOCATIONS, key=len, reverse=True):
        text = re.sub(
            rf"\b{re.escape(location.lower())}\b",
            " ",
            text
        )

    # Remove experience expressions.
    for patterns in EXPERIENCE_PATTERNS.values():
        for pattern in patterns:
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    removals = [
        r"\bfind\b",
        r"\bshow me\b",
        r"\bsearch for\b",
        r"\bi want\b",
        r"\bi need\b",
        r"\blooking for\b",
        r"\bfind me\b",
        r"\bjobs?\b",
        r"\bjob openings?\b",
        r"\bopportunities?\b",
        r"\brole\b",
        r"\broles\b",
        r"\bposition\b",
        r"\bpositions\b",
        r"\bwith\b",
        r"\bat\b",
        r"\bin\b",
        r"\bnear\b",
        r"\bpreferably\b",
        r"\bprefer\b",
        r"\bposted\b",
        r"\brecently\b",
        r"\brecent\b",
        r"\btoday\b",
        r"\byesterday\b",
        r"\bthis week\b",
        r"\blast week\b",
        r"\bthis month\b",
        r"\blast month\b",
        r"\bthe last\b",
        r"\bthe past\b",
        r"\blast\b",
        r"\bpast\b",
        r"\bprevious\b",
        r"\bdays?\b",
        r"\bweeks?\b",
        r"\bmonths?\b",
        r"\band\b",
        r"\bor\b",
        r"\bme\b",
        r"\bi\b",
        r"\bfor\b",
    ]

    for pattern in removals:
        text = re.sub(
            pattern,
            " ",
            text,
            flags=re.IGNORECASE
        )

    # Remove numbers left over from recency expressions.
    text = re.sub(r"\b\d+\b", " ", text)

    # Remove punctuation.
    text = re.sub(r"[^\w+#.\s-]", " ", text)

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text



def parse_query(query):
    """
    Convert a natural-language job-search query into structured filters.

    Returns:
        {
            "original_query": ...,
            "job_title": ...,
            "location": ...,
            "skills": [...],
            "experience_level": ...,
            "recency_days": ...,
            "search_keywords": ...
        }
    """

    if not query or not query.strip():
        return {
            "original_query": "",
            "job_title": None,
            "location": "India",
            "skills": [],
            "experience_level": None,
            "recency_days": 30,
            "search_keywords": "",
        }

    query = query.strip()

    skills = extract_skills(query)

    return {
        "original_query": query,
        "job_title": _find_job_title(query),
        "location": _find_location(query),
        "skills": skills,
        "experience_level": _find_experience_level(query),
        "recency_days": _find_recency(query),
        "search_keywords": _clean_search_keywords(query),
    }


if __name__ == "__main__":

    test_queries = [
        "Find me entry-level Python developer jobs in Bangalore",
        "Show me Python or Java developer jobs in Pune posted recently",
        "I want junior software engineer jobs in Hyderabad",
        "Find senior backend developer jobs in Delhi",
        "Looking for machine learning engineer jobs with Python and AWS in Bangalore",
        "Find remote React developer jobs posted in the last 2 weeks",
    ]

    print("\n🤖 NATURAL LANGUAGE QUERY PARSER")
    print("=" * 70)

    for query in test_queries:

        result = parse_query(query)

        print(f"\nQuery: {query}")
        print("-" * 70)

        print(f"Job title:        {result['job_title']}")
        print(f"Location:         {result['location']}")
        print(f"Skills:           {', '.join(result['skills']) or 'None'}")
        print(f"Experience:       {result['experience_level'] or 'Any'}")
        print(f"Recency:          {result['recency_days']} days")
        print(f"Search keywords:  {result['search_keywords']}")