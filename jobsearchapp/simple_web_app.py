from flask import Flask, render_template, request, jsonify

from simple_job_search import SimpleJobSearch
from query_parser import parse_query
from job_matcher import match_jobs_with_resume
from job_enricher import enrich_jobs
from query_relevance import rank_jobs_by_query


app = Flask(__name__)

searcher = SimpleJobSearch()


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():
    return render_template("simple_search.html")


# =========================================================
# JOB SEARCH API
# =========================================================

@app.route("/search", methods=["POST"])
def search_jobs():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No search data received"
            }), 400

        # ---------------------------------------------------------
        # 1. Parse search request
        # ---------------------------------------------------------

        query = data.get("query", "").strip()

        if query:

            parsed = parse_query(query)

            job_title = parsed.get(
                "job_title",
                "Software Engineer"
            )

            location = parsed.get(
                "location",
                "India"
            )

            recency_days = parsed.get(
                "recency_days",
                30
            )

        else:

            parsed = None

            job_title = data.get(
                "job_title",
                "Software Engineer"
            ).strip()

            location = data.get(
                "location",
                "India"
            ).strip()

            recency_days = int(
                data.get(
                    "recency_days",
                    30
                )
            )

        # ---------------------------------------------------------
        # Display parsed query in terminal
        # ---------------------------------------------------------

        print("\n🧠 Parsed Search Query")
        print("=" * 50)

        print(
            f"Job title:       {job_title}"
        )

        print(
            f"Location:        {location}"
        )

        print(
            f"Skills:          "
            f"{parsed.get('skills') if parsed else 'None'}"
        )

        print(
            f"Experience:      "
            f"{parsed.get('experience_level') if parsed else 'Any'}"
        )

        print(
            f"Recency:         {recency_days} days"
        )

        # ---------------------------------------------------------
        # 2. Search LinkedIn
        # ---------------------------------------------------------

        print("\n🚀 Starting job search...")
        print("=" * 50)

        jobs = searcher.search_jobs(
            job_title,
            location,
            recency_days=recency_days
        )

        print(
            f"\n✅ Total jobs found: {len(jobs)}"
        )

        # ---------------------------------------------------------
        # 3. Enrich LinkedIn job details
        # ---------------------------------------------------------

        try:

            jobs = enrich_jobs(jobs)

            print(
                f"📄 Enriched {len(jobs)} "
                f"jobs with detailed information"
            )

        except Exception as e:

            print(
                f"⚠️ Job enrichment failed: {e}"
            )

        # ---------------------------------------------------------
        # 4. AI Resume Matching
        # ---------------------------------------------------------

        try:

            jobs = match_jobs_with_resume(
                jobs,
                "resume.pdf"
            )

            print(
                f"🤖 AI matched {len(jobs)} "
                f"jobs against resume"
            )

        except Exception as e:

            print(
                f"⚠️ AI matching failed: {e}"
            )

            # Keep search functional even if
            # the AI matcher fails.

            for job in jobs:

                job["semantic_score"] = None
                job["skill_score"] = None
                job["final_score"] = None

        # ---------------------------------------------------------
        # 5. Final Query Relevance Ranking
        # ---------------------------------------------------------

        jobs = rank_jobs_by_query(
            job_title,
            location,
            jobs
        )

        print(
            "📊 Final query relevance ranking completed"
        )

        # ---------------------------------------------------------
        # Display ranking information
        # ---------------------------------------------------------

        for index, job in enumerate(jobs, start=1):

            print(
                f"{index}. "
                f"{job.get('title', 'Unknown')} — "
                f"{job.get('company', 'Unknown')} | "
                f"Query relevance: "
                f"{job.get('query_relevance_score', 0):.1f}"
            )

        # ---------------------------------------------------------
        # 6. Return response to frontend
        # ---------------------------------------------------------

        return jsonify({

            "success": True,

            "jobs": jobs,

            "count": len(jobs),

            "parsed_query": parsed

        })

    # =========================================================
    # GLOBAL ERROR HANDLER
    # =========================================================

    except Exception as e:

        print("\n❌ SEARCH ERROR")
        print("=" * 50)
        print(str(e))

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# RUN FLASK APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )