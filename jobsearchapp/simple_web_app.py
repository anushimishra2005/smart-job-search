from flask import Flask, render_template, request, jsonify, session
from pathlib import Path
from werkzeug.utils import secure_filename
from uuid import uuid4
import os

from simple_job_search import SimpleJobSearch
from query_parser import parse_query
from job_matcher import match_jobs_with_resume
from job_enricher import enrich_jobs
from query_relevance import rank_jobs_by_query
from overall_ranking import rank_jobs

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "dev-secret-key-change-in-production"
)

searcher = SimpleJobSearch()


# =========================================================
# RESUME UPLOAD CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_FOLDER = BASE_DIR / "uploads"

ALLOWED_RESUME_EXTENSIONS = {
    ".pdf",
    ".docx"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

UPLOAD_FOLDER.mkdir(exist_ok=True)


def allowed_resume_file(filename):
    """Check whether the uploaded file is a supported resume format."""

    extension = Path(filename).suffix.lower()

    return extension in ALLOWED_RESUME_EXTENSIONS
def build_match_explanation(job):
    """Build a human-readable explanation from existing match scores."""

    reasons = []

    resume_score = job.get("resume_match_score")
    query_score = job.get("query_relevance_score")
    freshness_score = job.get("freshness_score")

    # Resume similarity
    if resume_score is not None:
        if resume_score >= 80:
            reasons.append("Strong resume similarity")
        elif resume_score >= 60:
            reasons.append("Good resume similarity")
        elif resume_score >= 40:
            reasons.append("Moderate resume similarity")

    # Matched skills
    matched_skills = job.get("matched_skills") or []

    if matched_skills:
        if isinstance(matched_skills, str):
            matched_skills = [
                skill.strip()
                for skill in matched_skills.split(",")
                if skill.strip()
            ]

        if len(matched_skills) <= 3:
            reasons.append(
                f"Matching skills: {', '.join(matched_skills)}"
            )
        else:
            reasons.append(
                f"{len(matched_skills)} matching skills"
            )

    # Query relevance
    if query_score is not None and query_score >= 80:
        reasons.append("Strong match to your search")

    # Location
    location_score = job.get("location_match_score")

    if location_score is not None and location_score >= 80:
        reasons.append("Location matches your search")

    # Freshness
    if freshness_score is not None:
        if freshness_score >= 80:
            reasons.append("Recently posted")
        elif freshness_score >= 50:
            reasons.append("Posted recently")

    # Skill gaps
    missing_skills = job.get("missing_skills") or []

    if isinstance(missing_skills, str):
        missing_skills = [
            skill.strip()
            for skill in missing_skills.split(",")
            if skill.strip()
        ]

    return {
        "reasons": reasons,
        "skill_gaps": missing_skills
    }

# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():
    return render_template("simple_search.html")


# =========================================================
# RESUME UPLOAD API
# =========================================================

@app.route("/upload-resume", methods=["POST"])
def upload_resume():

    try:

        if "resume" not in request.files:

            return jsonify({
                "success": False,
                "error": "No resume file uploaded"
            }), 400

        resume = request.files["resume"]

        if resume.filename == "":

            return jsonify({
                "success": False,
                "error": "No resume selected"
            }), 400

        if not allowed_resume_file(resume.filename):

            return jsonify({
                "success": False,
                "error": "Unsupported resume format. Please upload a PDF or DOCX file."
            }), 400

        filename = secure_filename(resume.filename)

        if not filename:

            return jsonify({
                "success": False,
                "error": "Invalid filename"
            }), 400

        # ---------------------------------------------------------
        # Generate unique server-side filename
        # ---------------------------------------------------------

        extension = Path(filename).suffix.lower()

        unique_filename = f"{uuid4().hex}{extension}"

        file_path = UPLOAD_FOLDER / unique_filename

        resume.save(file_path)

        print("\n📄 Resume uploaded")
        print("=" * 50)
        print(f"Original filename: {filename}")
        print(f"Stored filename:   {unique_filename}")
        print(f"Path:              {file_path}")

        # ---------------------------------------------------------
        # Verify uploaded resume can be parsed
        # ---------------------------------------------------------

        from resume_parser import extract_resume_text

        resume_text = extract_resume_text(file_path)

        if not resume_text.strip():

            file_path.unlink(missing_ok=True)

            return jsonify({
                "success": False,
                "error": "The uploaded resume contains no readable text."
            }), 400

        print(
            f"Characters extracted: {len(resume_text)}"
        )

        # ---------------------------------------------------------
        # Store resume in current browser session
        # ---------------------------------------------------------

        session["resume_path"] = str(file_path)
        session["resume_filename"] = filename

        # ---------------------------------------------------------
        # Return safe information to frontend
        # ---------------------------------------------------------

        return jsonify({

            "success": True,

            "message": "Resume uploaded successfully",

            "filename": filename,

            "text_length": len(resume_text)

        })

    except Exception as e:

        print("\n❌ RESUME UPLOAD ERROR")
        print("=" * 50)
        print(str(e))

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# JOB SEARCH API
# =========================================================
def filter_jobs(jobs, location="", experience="", employment_type="", recency_days=""):
    """
    Apply structured filters to the enriched job results.
    Empty filter values mean 'Any'.
    """

    filtered_jobs = jobs

    # ---------------------------------------------------------
    # Location filter
    # ---------------------------------------------------------
    if location:
        location_lower = location.lower()

        def matches_location(job):
            job_location = str(job.get("location") or "").lower()

            if location_lower == "india":
                return "india" in job_location or "remote" in job_location

            if location_lower == "delhi":
                return any(
                    place in job_location
                    for place in [
                        "delhi",
                        "new delhi",
                        "gurgaon",
                        "gurugram",
                        "noida",
                        "faridabad",
                        "ghaziabad"
                    ]
                )

            if location_lower == "remote":
                return "remote" in job_location

            return location_lower in job_location

        filtered_jobs = [
            job for job in filtered_jobs
            if matches_location(job)
        ]

        # ---------------------------------------------------------
    # Experience filter
    # ---------------------------------------------------------
    if experience:
        experience_lower = experience.lower()

        def matches_experience(job):
            title = str(job.get("title") or "").lower()
            experience_text = str(job.get("experience") or "").lower()

            text = f"{title} {experience_text}"
            

            if experience_lower == "entry-level":
                return any(term in text for term in [
                    "entry level",
                    "entry-level",
                    "fresher",
                    "trainee",
                    "intern",
                    "internship"
                ])

            if experience_lower == "junior":
                return any(term in text for term in [
                    "junior",
                    "jr.",
                    "jr "
                ])

            if experience_lower == "mid":
                return any(term in text for term in [
                    "mid level",
                    "mid-level"
                ])

            if experience_lower == "senior":
                return any(term in text for term in [
                    "senior",
                    "sr.",
                    "sr ",
                    "lead",
                    "principal",
                    "staff"
                ])

            return True

        filtered_jobs = [
            job for job in filtered_jobs
            if matches_experience(job)
        ]
    # ---------------------------------------------------------
    # Employment type filter
    # ---------------------------------------------------------
    if employment_type:
        employment_lower = employment_type.lower()

        filtered_jobs = [
            job for job in filtered_jobs
            if str(job.get("employment_type") or "").lower()
            == employment_lower
        ]

    # ---------------------------------------------------------
    # Recency filter
    # ---------------------------------------------------------
    if recency_days:
        try:
            from datetime import datetime

            days = max(int(recency_days), 1)
            today = datetime.now().date()

            def matches_recency(job):
                posted_date = job.get("posted_date")

                if not posted_date:
                    return False

                try:
                    posted = datetime.strptime(
                        str(posted_date)[:10],
                        "%Y-%m-%d"
                    ).date()

                    age = (today - posted).days

                    return 0 <= age <= days

                except (ValueError, TypeError):
                    return False

            filtered_jobs = [
                job for job in filtered_jobs
                if matches_recency(job)
            ]

        except (ValueError, TypeError):
            pass

    return filtered_jobs
@app.route("/search", methods=["POST"])
def search_jobs():

    try:

        data = request.get_json()
        # ---------------------------------------------------------
        # Structured search filters
        # ---------------------------------------------------------

        filter_location = data.get("filter_location", "").strip()
        filter_experience = data.get("filter_experience", "").strip()
        filter_employment = data.get("filter_employment", "").strip()
        filter_recency = data.get("filter_recency", "").strip()
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
        # Display parsed query
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
        # 3.5 Apply structured filters
        # ---------------------------------------------------------

        jobs_before_filter = len(jobs)

        jobs = filter_jobs(
            jobs,
            location=filter_location,
            experience=filter_experience,
            employment_type=filter_employment,
            recency_days=filter_recency
        )

        print(
            f"🔎 Structured filters: "
            f"{jobs_before_filter} → {len(jobs)} jobs"
        )

        print(
            f"   Location: {filter_location or 'Any'}"
        )

        print(
            f"   Experience: {filter_experience or 'Any'}"
        )

        print(
            f"   Employment: {filter_employment or 'Any'}"
        )

        print(
            f"   Recency: "
            f"{filter_recency + ' days' if filter_recency else 'Any'}"
        )
        # ---------------------------------------------------------
        # 4. AI Resume Matching
        # ---------------------------------------------------------

        try:

            resume_path = session.get("resume_path")

            if not resume_path:

                return jsonify({
                    "success": False,
                    "error": "Please upload your resume before searching for jobs."
                }), 400

            resume_file = Path(resume_path)

            if not resume_file.exists():

                session.pop("resume_path", None)
                session.pop("resume_filename", None)

                return jsonify({
                    "success": False,
                    "error": "Uploaded resume is no longer available. Please upload it again."
                }), 400

            jobs = match_jobs_with_resume(
                jobs,
                str(resume_file)
            )

            print(
                f"🤖 AI matched {len(jobs)} "
                f"jobs against uploaded resume"
            )

        except Exception as e:

            print(
                f"⚠️ AI matching failed: {e}"
            )

            for job in jobs:

                job["semantic_score"] = None
                job["skill_score"] = None
                job["final_score"] = None

        # ---------------------------------------------------------
        # 5. Final Overall Ranking
        # ---------------------------------------------------------

        jobs = rank_jobs(
            job_title,
            location,
            jobs,
            recency_days
        )

        print(
            "📊 Final overall ranking completed"
        )
        # ---------------------------------------------------------
        # 5.5 Build match explanations
        # ---------------------------------------------------------

        for job in jobs:
            job["why_this_matches"] = build_match_explanation(job)
        # ---------------------------------------------------------
        # Display ranking information
        # ---------------------------------------------------------

        for index, job in enumerate(jobs, start=1):

            print(
                f"{index}. "
                f"{job.get('title', 'Unknown')} — "
                f"{job.get('company', 'Unknown')} | "
                f"Overall: {job.get('overall_match_score', 0):.1f} | "
                f"Resume: {job.get('resume_match_score', 0):.1f} | "
                f"Query: {job.get('query_relevance_score', 0):.1f} | "
                f"Freshness: {job.get('freshness_score', 0):.1f}"
            )

        # ---------------------------------------------------------
        # 6. Return response
        # ---------------------------------------------------------

        return jsonify({

            "success": True,

            "jobs": jobs,

            "count": len(jobs),

            "parsed_query": parsed

        })

    except Exception as e:

        import traceback

        print("\n❌ SEARCH ERROR")
        print("=" * 50)
        print(f"Error type: {type(e).__name__}")
        print(f"Error: {e}")
        traceback.print_exc()

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