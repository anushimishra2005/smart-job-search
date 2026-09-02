from query_relevance import calculate_query_relevance, rank_jobs_by_query


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


print("\nQUERY RELEVANCE TEST")
print("=" * 60)

ranked_jobs = rank_jobs_by_query(
    query_title,
    query_location,
    jobs
)

for job in ranked_jobs:
    print(
        f"{job['title']:<30} | "
        f"{job['location']:<20} | "
        f"Title: {job['title_match_score']:>6.1f} | "
        f"Location: {job['location_match_score']:>6.1f} | "
        f"Query: {job['query_relevance_score']:>6.1f}"
    )