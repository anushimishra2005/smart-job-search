from query_relevance import calculate_query_relevance, rank_jobs_by_query


def test_query_relevance():
    query_title = "Software Developer"
    query_location = "Delhi"

    jobs = [
        {
            "title": "Software Developer",
            "location": "Delhi"
        },
        {
            "title": "Software Engineer II",
            "location": "Miamisburg, OH"
        },
        {
            "title": "Python Developer",
            "location": "Delhi"
        },
        {
            "title": "Senior Software Developer",
            "location": "Noida, India"
        },
        {
            "title": "Software Engineer",
            "location": "Remote"
        }
    ]

    ranked_jobs = rank_jobs_by_query(
        query_title,
        query_location,
        jobs
    )

    # Exact title + exact location should be the strongest match.
    assert ranked_jobs[0]["title"] == "Software Developer"
    assert ranked_jobs[0]["query_relevance_score"] == 100.0

    # Exact location should receive full location relevance.
    assert ranked_jobs[0]["location_match_score"] == 100.0

    # Python Developer shares the "developer" role token.
    python_job = next(
        job for job in ranked_jobs
        if job["title"] == "Python Developer"
    )

    assert python_job["title_match_score"] == 50.0
    assert python_job["location_match_score"] == 100.0
    assert python_job["query_relevance_score"] == 65.0

    # A job outside the requested location should receive
    # zero location relevance.
    ohio_job = next(
        job for job in ranked_jobs
        if job["title"] == "Software Engineer II"
    )

    assert ohio_job["location_match_score"] == 0.0

    # Remote jobs receive partial location compatibility.
    remote_job = next(
        job for job in ranked_jobs
        if job["location"] == "Remote"
    )

    assert remote_job["location_match_score"] == 50.0


if __name__ == "__main__":
    test_query_relevance()
    print("All query relevance tests passed.")