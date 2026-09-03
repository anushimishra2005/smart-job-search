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