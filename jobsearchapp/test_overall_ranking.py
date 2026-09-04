from overall_ranking import (
    calculate_freshness_score,
    calculate_overall_match_score,
    rank_jobs
)


jobs = [

    {
        "title": "Python Developer",
        "location": "India",
        "posted_date": "2026-09-02",
        "final_score": 40.0
    },

    {
        "title": "Custom Software Engineer",
        "location": "Bhubaneswar, Odisha, India",
        "posted_date": "2026-09-01",
        "final_score": 80.0
    },

    {
        "title": "Python Developer",
        "location": "India",
        "posted_date": "2026-08-20",
        "final_score": 70.0
    }
]


print("Freshness test")
print("=" * 50)

print(
    "Today:",
    calculate_freshness_score(
        "2026-09-02",
        30
    )
)

print(
    "Yesterday:",
    calculate_freshness_score(
        "2026-09-01",
        30
    )
)

print(
    "Older job:",
    calculate_freshness_score(
        "2026-08-20",
        30
    )
)


print("\nOverall score test")
print("=" * 50)

print(
    calculate_overall_match_score(
        80,
        70,
        90
    )
)


print("\nRanked jobs")
print("=" * 50)

ranked_jobs = rank_jobs(
    "Python Developer",
    "India",
    jobs,
    recency_days=30
)


for index, job in enumerate(
    ranked_jobs,
    start=1
):

    print(
        f"{index}. "
        f"{job['title']} | "
        f"AI: {job['resume_match_score']} | "
        f"Query: {job['query_relevance_score']} | "
        f"Freshness: {job['freshness_score']} | "
        f"Overall: {job['overall_match_score']}"
    )