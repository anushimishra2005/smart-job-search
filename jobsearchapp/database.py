import sqlite3
from datetime import datetime


DATABASE_NAME = "jobs.db"


def get_connection():
    """Create and return a SQLite database connection."""
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def create_jobs_table():
    """Create the jobs table if it does not already exist."""
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            experience TEXT,
            salary TEXT,
            description TEXT,
            posted_date TEXT,
            posted_text TEXT,
            apply_url TEXT NOT NULL,
            source TEXT NOT NULL,
            scraped_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def save_jobs(jobs):
    """Save jobs to the database while avoiding duplicate listings."""
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
                posted_date,
                posted_text,
                apply_url,
                source,
                scraped_at
            )
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
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