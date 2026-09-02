import sqlite3

from resume_parser import extract_resume_text
from skill_extractor import extract_skills
from sentence_transformers import SentenceTransformer, util


DATABASE_NAME = "jobs.db"

# Lightweight general-purpose sentence embedding model.
MODEL_NAME = "all-MiniLM-L6-v2"

print("🧠 Loading semantic model...")
model = SentenceTransformer(MODEL_NAME)
print("✅ Semantic model loaded")


def calculate_skill_match(resume_skills, job_skills):
    """Calculate technical skill overlap."""

    resume_set = set(resume_skills)
    job_set = set(job_skills)

    if not job_set:
        return {
            "skill_score": None,
            "matched_skills": [],
            "missing_skills": [],
            "job_skill_count": 0
        }

    matched = sorted(resume_set.intersection(job_set))
    missing = sorted(job_set - resume_set)

    score = round(
        (len(matched) / len(job_set)) * 100,
        2
    )

    return {
        "skill_score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "job_skill_count": len(job_set)
    }


def calculate_semantic_score(resume_text, job_description):
    """
    Calculate semantic similarity between resume and job description.
    """

    if not resume_text or not job_description:
        return 0.0

    embeddings = model.encode(
        [resume_text, job_description],
        convert_to_tensor=True
    )

    similarity = util.cos_sim(
        embeddings[0],
        embeddings[1]
    ).item()

    # Convert cosine similarity to percentage.
    score = max(0.0, min(100.0, similarity * 100))

    return round(score, 2)


def calculate_final_score(semantic_score, skill_score):
    """
    Combine semantic and skill scores.

    If technical skill information is unavailable,
    semantic similarity remains the primary score.
    """

    if skill_score is None:
        return round(semantic_score, 2)

    # Semantic understanding is weighted more heavily.
    final_score = (
        semantic_score * 0.70
        + skill_score * 0.30
    )

    return round(final_score, 2)


def get_jobs():
    """Load stored jobs from SQLite."""

    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row

    jobs = connection.execute("""
        SELECT
            id,
            title,
            company,
            location,
            description
        FROM jobs
        WHERE description IS NOT NULL
          AND description != ''
    """).fetchall()

    connection.close()

    return [dict(job) for job in jobs]
def match_jobs_with_resume(jobs, resume_path="resume.pdf"):
    """
    Calculate AI resume match scores for a supplied list of jobs.
    """

    resume_text = extract_resume_text(resume_path)
    resume_skills = extract_skills(resume_text)

    results = []

    for job in jobs:

        description = job.get("description", "") or ""

        job_skills = extract_skills(description)

        skill_match = calculate_skill_match(
            resume_skills,
            job_skills
        )

        semantic_score = calculate_semantic_score(
            resume_text,
            description
        )

        final_score = calculate_final_score(
            semantic_score,
            skill_match["skill_score"]
        )

        result = {
            **job,
            "job_skills": job_skills,
            "semantic_score": semantic_score,
            "skill_score": skill_match["skill_score"],
            "final_score": final_score,
            "score": final_score,
            "matched_skills": skill_match["matched_skills"],
            "missing_skills": skill_match["missing_skills"],
            "job_skill_count": skill_match["job_skill_count"]
        }

        results.append(result)

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results

def match_resume_to_jobs(resume_path="resume.pdf"):
    """Match all stored jobs against the resume."""

    print("📄 Loading resume...")

    resume_text = extract_resume_text(resume_path)
    resume_skills = extract_skills(resume_text)

    print(
        f"✅ Resume loaded: "
        f"{len(resume_skills)} skills detected"
    )

    print("\n🤖 AI JOB MATCHING")
    print("=" * 70)

    jobs = get_jobs()

    return match_jobs_with_resume(
        jobs,
        resume_path
    )

def display_results(results):
    """Display AI resume-job matching results."""

    print("\n🎯 RESUME → JOB MATCHING")
    print("=" * 70)

    for index, job in enumerate(results, 1):

        print(
            f"\n{index}. {job['title']}"
            f" — {job['company']}"
        )

        print(
            f"   🎯 Final Match: "
            f"{job['score']}%"
        )

        print(
            f"   🧠 Semantic Score: "
            f"{job['semantic_score']}%"
        )

        if job["skill_score"] is not None:

            print(
                f"   🛠 Skill Match: "
                f"{job['skill_score']}%"
            )

            if job["matched_skills"]:

                print("\n   ✅ Matched skills:")

                for skill in job["matched_skills"]:
                    print(f"      ✓ {skill}")

            if job["missing_skills"]:

                print("\n   ❌ Missing skills:")

                for skill in job["missing_skills"]:
                    print(f"      — {skill}")

        else:

            print(
                "   🛠 Skill Match: "
                "Insufficient skill data"
            )


if __name__ == "__main__":

    results = match_resume_to_jobs()

    display_results(results)