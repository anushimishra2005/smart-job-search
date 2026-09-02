import re


STOP_WORDS = {
    "a", "an", "the", "and", "or",
    "for", "in", "on", "at", "to",
    "with", "job", "jobs"
}


SENIORITY_WORDS = {
    "intern",
    "internship",
    "trainee",
    "junior",
    "jr",
    "senior",
    "sr",
    "lead",
    "principal",
    "staff",
    "manager",
    "director",
    "head",
    "architect"
}


def normalize_text(text):
    """Normalize text for comparison."""

    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_tokens(text):
    """Convert text into useful words."""

    normalized = normalize_text(text)

    return {
        word
        for word in normalized.split()
        if word not in STOP_WORDS
    }


def get_role_tokens(text):
    """Remove seniority words and keep role-related words."""

    tokens = get_tokens(text)

    return {
        word
        for word in tokens
        if word not in SENIORITY_WORDS
    }


def calculate_title_match(query_title, job_title):
    """
    Calculate job title similarity from 0 to 100.
    """

    query_title = normalize_text(query_title)
    job_title = normalize_text(job_title)

    if not query_title or not job_title:
        return 0.0

    # Exact title match
    if query_title == job_title:
        return 100.0

    query_tokens = get_role_tokens(query_title)
    job_tokens = get_role_tokens(job_title)

    if not query_tokens or not job_tokens:
        return 0.0

    matched_tokens = query_tokens.intersection(job_tokens)

    if not matched_tokens:
        return 0.0

    # Percentage of requested role words that matched
    query_coverage = len(matched_tokens) / len(query_tokens)

    # Percentage of job role words that matched
    job_coverage = len(matched_tokens) / len(job_tokens)

    # Balanced similarity score
    similarity = (
        2 * query_coverage * job_coverage
        / (query_coverage + job_coverage)
    )

    score = similarity * 100

    # Strong partial match when the complete query appears
    # inside the job title.
    if query_title in job_title:
        score = max(score, 90.0)

    return round(min(score, 100.0), 2)


def calculate_location_match(query_location, job_location):
    """Calculate location compatibility from 0 to 100."""

    query_location = normalize_text(query_location)
    job_location = normalize_text(job_location)

    if not query_location or not job_location:
        return 0.0

    # India-wide search
    if query_location == "india":
        if "india" in job_location:
            return 100.0

    # Exact location
    if query_location == job_location:
        return 100.0

    # Requested location contained in job location
    if query_location in job_location:
        return 100.0

    # Remote jobs get partial compatibility
    if "remote" in job_location:
        return 50.0

    return 0.0


def calculate_query_relevance(query_title, query_location, job):
    """
    Calculate how relevant a job is to the user's search.

    Title = 70%
    Location = 30%
    """

    title_score = calculate_title_match(
        query_title,
        job.get("title", "")
    )

    location_score = calculate_location_match(
        query_location,
        job.get("location", "")
    )

    query_score = (
        title_score * 0.70 +
        location_score * 0.30
    )

    return {
        "title_match_score": round(title_score, 2),
        "location_match_score": round(location_score, 2),
        "query_relevance_score": round(query_score, 2)
    }


def rank_jobs_by_query(query_title, query_location, jobs):
    """Add query relevance scores and rank jobs."""

    ranked_jobs = []

    for job in jobs:

        relevance = calculate_query_relevance(
            query_title,
            query_location,
            job
        )

        ranked_job = {
            **job,
            **relevance
        }

        ranked_jobs.append(ranked_job)

    ranked_jobs.sort(
        key=lambda job: job["query_relevance_score"],
        reverse=True
    )

    return ranked_jobs