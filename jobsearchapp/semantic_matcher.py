import sqlite3

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from resume_parser import extract_resume_text
from skill_extractor import extract_skills
from job_matcher import calculate_match


DATABASE_NAME = "jobs.db"
MODEL_NAME = "all-MiniLM-L6-v2"


class SemanticJobMatcher:
    """AI-powered resume to job matching engine."""

    def __init__(self, resume_path="resume.pdf"):
        print("🤖 Loading AI embedding model...")

        self.model = SentenceTransformer(MODEL_NAME)

        print("📄 Loading resume...")

        self.resume_text = extract_resume_text(resume_path)
        self.resume_skills = extract_skills(self.resume_text)

        print(
            f"✅ Resume loaded: "
            f"{len(self.resume_skills)} skills detected"
        )

    def build_job_text(self, job):
        """Build text representation of a job."""

        return " ".join([
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("description", "")
        ])

    def semantic_score(self, job_text):
        """Calculate semantic similarity."""

        resume_embedding = self.model.encode(
            [self.resume_text],
            normalize_embeddings=True
        )

        job_embedding = self.model.encode(
            [job_text],
            normalize_embeddings=True
        )

        similarity = cosine_similarity(
            resume_embedding,
            job_embedding
        )[0][0]

        return round(float(similarity) * 100, 2)

    def rank_jobs(self, jobs):
        """Rank supplied jobs using semantic + skill matching."""

        results = []

        for job in jobs:

            job_text = self.build_job_text(job)

            semantic = self.semantic_score(job_text)

            job_skills = extract_skills(
                job.get("description", "")
            )

            skill_match = calculate_match(
                self.resume_skills,
                job_skills
            )

            if skill_match["score"] is None:

                final_score = semantic
                skill_score = None

            else:

                skill_score = skill_match["score"]

                final_score = round(
                    (semantic * 0.70)
                    + (skill_score * 0.30),
                    2
                )

            matched_skills = skill_match["matched_skills"]
            missing_skills = skill_match["missing_skills"]

            # -----------------------------------------
            # Generate explainable recommendations
            # -----------------------------------------

            match_reasons = []

            for skill in matched_skills:
                match_reasons.append(
                    f"{skill} appears in both your resume and the job requirements."
                )

            gap_reasons = []

            for skill in missing_skills:
                gap_reasons.append(
                    f"{skill} is mentioned in the job but was not detected in your resume."
                )

            # If no explicit skills were detected, explain that
            if not job_skills:
                match_reasons.append(
                    "The job description does not contain enough recognized technical skills "
                    "for a detailed skill comparison."
                )

            results.append({
                **job,

                "semantic_score": semantic,

                "skill_score": skill_score,

                "final_score": final_score,

                "job_skills": job_skills,

                "matched_skills": matched_skills,

                "missing_skills": missing_skills,

                "match_reasons": match_reasons,

                "gap_reasons": gap_reasons
            })
            for result in results:

                score = result["final_score"]

                if score >= 70:
                    recommendation = "Strong Match"
                elif score >= 50:
                    recommendation = "Good Match"
                elif score >= 30:
                    recommendation = "Moderate Match"
                else:
                    recommendation = "Low Match"

                result["recommendation"] = recommendation

        results.sort(
            key=lambda job: job["final_score"],
            reverse=True
        )

        return results


# Load once when imported by Flask.
matcher = SemanticJobMatcher()


def rank_jobs(jobs):
    """Public function used by the Flask application."""

    return matcher.rank_jobs(jobs)


if __name__ == "__main__":

    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row

    jobs = connection.execute("""
        SELECT
            id,
            title,
            company,
            location,
            description,
            posted_date,
            posted_text,
            apply_url,
            source
        FROM jobs
        WHERE description IS NOT NULL
          AND description != ''
    """).fetchall()

    connection.close()

    jobs = [dict(job) for job in jobs]

    results = rank_jobs(jobs)

    print("\n🧠 AI JOB RANKING")
    print("=" * 75)

    for index, job in enumerate(results, 1):

        print(
            f"\n{index}. {job['title']}"
            f" — {job['company']}"
        )

        print(
            f"   🎯 Final Match: "
            f"{job['final_score']}%"
        )

        print(
            f"   🧠 Semantic: "
            f"{job['semantic_score']}%"
        )

        if job["skill_score"] is not None:
            print(
                f"   🛠 Skills: "
                f"{job['skill_score']}%"
            )

        if job["matched_skills"]:
            print(
                "   ✅ Matched: "
                + ", ".join(job["matched_skills"])
            )

        if job["missing_skills"]:
            print(
                "   ❌ Missing: "
                + ", ".join(job["missing_skills"])
            )