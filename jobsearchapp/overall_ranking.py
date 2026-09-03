from datetime import datetime


# =========================================================
# FRESHNESS SCORE
# =========================================================

def calculate_freshness_score(posted_date, recency_days=30):
    """
    Calculate how fresh a job is.

    100 = posted today
    0   = at or beyond the recency limit
    50  = unknown posting date
    """

    if not posted_date:
        return 50.0

    try:

        posted = datetime.strptime(
            str(posted_date)[:10],
            "%Y-%m-%d"
        ).date()

        today = datetime.now().date()

        age_days = max(
            0,
            (today - posted).days
        )

        recency_days = max(
            int(recency_days or 30),
            1
        )

        if age_days >= recency_days:
            return 0.0

        score = (
            1 - (age_days / recency_days)
        ) * 100

        return round(
            max(0.0, min(100.0, score)),
            2
        )

    except (ValueError, TypeError):

        return 50.0


# =========================================================
# OVERALL MATCH SCORE
# =========================================================

def calculate_overall_match_score(
    resume_match_score,
    query_relevance_score,
    freshness_score
):
    """
    Calculate the personalized job ranking score.

    Resume Match    = 50%
    Query Relevance = 30%
    Freshness       = 20%
    """

    if resume_match_score is None:

        # If AI matching is unavailable,
        # fall back to search relevance + freshness.

        score = (
            query_relevance_score * 0.60
            + freshness_score * 0.40
        )

        return round(
            max(0.0, min(100.0, score)),
            2
        )

    score = (
        resume_match_score * 0.50
        + query_relevance_score * 0.30
        + freshness_score * 0.20
    )

    return round(
        max(0.0, min(100.0, score)),
        2
    )


# =========================================================
# RANK JOBS
# =========================================================

def rank_jobs(
    query_title,
    query_location,
    jobs,
    recency_days=30
):
    """
    Add overall ranking information to every job.

    Existing job information is preserved.
    """

    # Import here to keep this module independent
    # from the existing query relevance implementation.
    from query_relevance import calculate_query_relevance

    ranked_jobs = []

    for job in jobs:

        # ---------------------------------------------------------
        # Query relevance
        # ---------------------------------------------------------

        relevance = calculate_query_relevance(
            query_title,
            query_location,
            job
        )

        # ---------------------------------------------------------
        # Resume match
        # ---------------------------------------------------------

        resume_match_score = job.get(
            "final_score"
        )

        if resume_match_score is not None:

            try:

                resume_match_score = float(
                    resume_match_score
                )

            except (ValueError, TypeError):

                resume_match_score = None

        # ---------------------------------------------------------
        # Freshness
        # ---------------------------------------------------------

        freshness_score = calculate_freshness_score(
            job.get("posted_date"),
            recency_days
        )

        # ---------------------------------------------------------
        # Overall score
        # ---------------------------------------------------------

        overall_score = calculate_overall_match_score(
            resume_match_score,
            relevance["query_relevance_score"],
            freshness_score
        )

        ranked_job = {
            **job,

            # Existing query relevance fields
            **relevance,

            # New ranking fields
            "resume_match_score": resume_match_score,
            "freshness_score": freshness_score,
            "overall_match_score": overall_score,

            # Keep score compatible with existing frontend
            "score": overall_score
        }

        ranked_jobs.append(ranked_job)

    # Highest overall score first
    ranked_jobs.sort(
        key=lambda job: job["overall_match_score"],
        reverse=True
    )

    return ranked_jobs
