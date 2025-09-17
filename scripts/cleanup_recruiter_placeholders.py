"""One-off cleanup script to remove synthetic recruiter placeholders.

Sets recruiter_name/email to NULL where they were previously fabricated.
Run once after deployment:
    python -m scripts.cleanup_recruiter_placeholders
"""

from sqlalchemy import update
from app.core.database import SessionLocal
from app.models.scraped_job import ScrapedJob

PLACEHOLDER_NAMES = {"Recruiter", "Recruiter Placeholder"}

def main():
    db = SessionLocal()
    try:
        q = db.query(ScrapedJob).filter(
            (ScrapedJob.recruiter_name.in_(PLACEHOLDER_NAMES)) |
            (ScrapedJob.recruiter_email.like('talent@%'))
        )
        count = q.count()
        if count:
            # Use bulk update for performance
            q.update({
                ScrapedJob.recruiter_name: None,
                ScrapedJob.recruiter_email: None
            }, synchronize_session=False)
            db.commit()
        print(f"Cleaned {count} jobs with placeholder recruiter data.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
