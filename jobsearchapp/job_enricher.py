import json
import html
import sqlite3
from bs4 import BeautifulSoup
import requests
from skill_extractor import extract_skills

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def extract_jobposting(page_html):
    """Extract Schema.org JobPosting JSON from LinkedIn."""

    soup = BeautifulSoup(page_html, "html.parser")

    for script in soup.find_all("script"):
        script_text = script.string or script.get_text()

        if not script_text:
            continue

        if '"@type":"JobPosting"' not in script_text and \
           '"@type": "JobPosting"' not in script_text:
            continue

        try:
            data = json.loads(script_text)

            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                return data

        except json.JSONDecodeError:
            pass

    return None


def clean_html(text):
    """Convert HTML description into readable text."""

    if not text:
        return ""

    text = html.unescape(text)

    soup = BeautifulSoup(text, "html.parser")

    return soup.get_text("\n", strip=True)


def enrich_job(job_url):
    """Fetch a LinkedIn job page and extract structured data."""

    response = requests.get(
        job_url,
        headers=HEADERS,
        timeout=15
    )

    response.raise_for_status()

    data = extract_jobposting(response.text)

    if not data:
        return None

    posted_date = data.get("datePosted")

    if posted_date:
        posted_date = posted_date[:10]

    description = clean_html(data.get("description", ""))
    structured_skills = data.get("skills", "")

    if structured_skills:
        skills = structured_skills
    else:
        skills = ", ".join(extract_skills(description))

    return {
        "description": description,
        "employment_type": data.get("employmentType"),
        "posted_date": posted_date,
        "skills": skills
    }


def update_database():
    """Enrich all jobs currently stored in SQLite."""

    connection = sqlite3.connect("jobs.db")
    cursor = connection.cursor()

    rows = cursor.execute(
        "SELECT id, apply_url FROM jobs"
    ).fetchall()

    print(f"🔍 Found {len(rows)} jobs to enrich")

    updated = 0

    for job_id, job_url in rows:

        print(f"\n🔎 Enriching Job {job_id}")

        try:
            info = enrich_job(job_url)

            if not info:
                print("   ⚠️ JobPosting data not found")
                continue

            cursor.execute(
                """
                UPDATE jobs
                SET description = ?,
                    employment_type = ?,
                    posted_date = ?,
                    skills = ?
                WHERE id = ?
                """,
                (
                    info["description"],
                    info["employment_type"],
                    info["posted_date"],
                    info["skills"],
                    job_id
                )
            )

            updated += 1

            print(
                f"   ✓ Description: "
                f"{len(info['description'])} characters"
            )

            print(
                f"   ✓ Employment: "
                f"{info['employment_type']}"
            )

            print(
                f"   ✓ Posted: "
                f"{info['posted_date']}"
            )

            print(
                f"   ✓ Skills: "
                f"{info['skills'] or 'Not provided'}"
            )

        except Exception as e:
            print(f"   ❌ Failed: {e}")

    connection.commit()
    connection.close()

    print(f"\n✅ Updated {updated} jobs.")

def enrich_jobs(jobs):
    """
    Enrich freshly scraped jobs before AI matching.

    Fetches each LinkedIn job detail page, extracts the
    full JobPosting description and updates the database.
    """

    connection = sqlite3.connect("jobs.db")
    cursor = connection.cursor()

    enriched_jobs = []

    print("\n🔎 ENRICHING JOB DETAILS")
    print("=" * 50)

    for job in jobs:

        job_url = job.get("apply_url")

        if not job_url:
            print(
                f"⚠️ No URL for: "
                f"{job.get('title', 'Unknown Job')}"
            )
            enriched_jobs.append(job)
            continue

        print(
            f"\n🔎 {job.get('title', 'Unknown Job')}"
            f" — {job.get('company', 'Unknown Company')}"
        )

        try:
            info = enrich_job(job_url)

            if not info:
                print("   ⚠️ JobPosting data not found")
                enriched_jobs.append(job)
                continue

            # Update the in-memory job object.
            # This is important because the AI matcher
            # receives this object immediately afterward.
            job["description"] = info["description"]
            job["employment_type"] = info["employment_type"]
            job["posted_date"] = info["posted_date"]
            job["skills"] = info["skills"]

            # Update SQLite as well.
            cursor.execute(
                """
                UPDATE jobs
                SET description = ?,
                    employment_type = ?,
                    posted_date = ?,
                    skills = ?
                WHERE apply_url = ?
                """,
                (
                    info["description"],
                    info["employment_type"],
                    info["posted_date"],
                    info["skills"],
                    job_url
                )
            )

            enriched_jobs.append(job)

            print(
                f"   ✓ Description: "
                f"{len(info['description'])} characters"
            )

            print(
                f"   ✓ Employment: "
                f"{info['employment_type'] or 'Not provided'}"
            )

            print(
                f"   ✓ Posted: "
                f"{info['posted_date'] or 'Not provided'}"
            )

            print(
                f"   ✓ Skills: "
                f"{info['skills'] or 'Not provided'}"
            )

        except Exception as e:

            print(f"   ❌ Failed: {e}")

            # Keep the original job so one failed
            # LinkedIn page doesn't break the entire search.
            enriched_jobs.append(job)

    connection.commit()
    connection.close()

    print(
        f"\n✅ Enriched {len(enriched_jobs)} jobs"
    )

    return enriched_jobs
if __name__ == "__main__":
    update_database()