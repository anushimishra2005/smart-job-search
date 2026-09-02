import sqlite3
from datetime import datetime


DATABASE_NAME = "jobs.db"


def get_connection():
    """Create and return a SQLite database connection."""
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def create_jobs_table():
    """Create the jobs table and upgrade an existing database if needed."""
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            experience TEXT,
            salary TEXT,
            description TEXT,
            skills TEXT,
            employment_type TEXT,
            posted_date TEXT,
            posted_text TEXT,
            apply_url TEXT UNIQUE,
            source TEXT,
            scraped_at TEXT
        )
    """)

    # Upgrade an existing jobs.db safely.
    existing_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
    }

    required_columns = {
        "skills": "TEXT",
        "employment_type": "TEXT",
        "posted_text": "TEXT",
        "scraped_at": "TEXT"
    }

    for column, data_type in required_columns.items():
        if column not in existing_columns:
            connection.execute(
                f"ALTER TABLE jobs ADD COLUMN {column} {data_type}"
            )
            print(f"➕ Added database column: {column}")

    connection.commit()
    connection.close()


def save_jobs(jobs):
    """Save jobs while avoiding duplicate application URLs."""
    connection = get_connection()

    for job in jobs:
        connection.execute("""
            INSERT INTO jobs (
                title,
                company,
                location,
                experience,
                salary,
                description,
                skills,
                employment_type,
                posted_date,
                posted_text,
                apply_url,
                source,
                scraped_at
            )
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1
                FROM jobs
                WHERE apply_url = ?
            )
        """, (
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("experience", ""),
            job.get("salary", ""),
            job.get("description", ""),
            job.get("skills"),
            job.get("employment_type"),
            job.get("posted_date"),
            job.get("posted_text"),
            job.get("apply_url", ""),
            job.get("source", "LinkedIn"),
            datetime.now().isoformat(),
            job.get("apply_url", "")
        ))

    connection.commit()
    connection.close()


def get_all_jobs():
    """Return all stored jobs, newest scraped jobs first."""
    connection = get_connection()

    jobs = connection.execute("""
        SELECT *
        FROM jobs
        ORDER BY scraped_at DESC
    """).fetchall()

    connection.close()

    return [dict(job) for job in jobs]


if __name__ == "__main__":
    create_jobs_table()
    print(f"✅ Database initialized: {DATABASE_NAME}")