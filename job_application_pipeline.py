#!/usr/bin/env python3
"""
Comprehensive job application pipeline.

This script ties together multiple services to automate parts of a job search workflow:

1. Collect user parameters (job title, location, company names and IDs, etc.).
2. Run a LinkedIn jobs scraping Actor on Apify using those parameters and fetch the results.
3. Persist the scraped jobs to JSON and into a local SQLite database with deduplication on the job ID.
4. Enrich each job with recruiter contact information using the Apollo API if the original
   poster's details are missing.
5. Read the user's resume from a file and compute a simple similarity score against each
   job's description. Select jobs that match above a configurable threshold.
6. For each matched job, create a customised version of the resume that highlights
   keywords from the job description and generate a cover letter addressed to the
   appropriate recruiter.
7. Send the customised resume and cover letter to the recruiter via SendGrid.

NOTE:
 - This script relies on several environment variables: `APIFY_TOKEN`, `APOLLO_API_KEY` and
   `SENDGRID_API_KEY`. These must be set for the relevant services to work. Without
   network connectivity or valid API keys, network operations will fail at runtime.
 - The similarity computation is intentionally simple (based on difflib's SequenceMatcher) and
   may not capture the nuance of resume-job matching. For real use, consider more
   sophisticated NLP techniques.
 - Running this script will attempt to send emails. You should only enable that part
   if you are ready to contact recruiters. The script includes a `--dry-run` option
   which skips sending emails and instead prints the generated content.
"""

import argparse
import json
import os
import re
import sqlite3
import requests
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Third‑party imports which may not be installed in all environments.  These
# imports are surrounded by try/except blocks where appropriate in order to
# avoid hard failures if the user does not need the associated functionality.

try:
    from apify_client import ApifyClient
except ImportError:
    ApifyClient = None  # type: ignore

try:
    import openai
except ImportError:
    openai = None  # type: ignore

# Import Apollo search helper from the local module.  If this fails due to
# missing API key or missing file, the enrich functionality will be disabled.
try:
    from apollotest import search_people
except (SystemExit, Exception):
    search_people = None  # type: ignore

from resume_convertion import convert_resume  # Local module for resume conversion from txt to docx
from coverletter_convertion import convert_cover_letter  # Local module for cover letter conversion

def look_people(company: str, title: str) -> List[Dict[str, Any]]:
    # Wrapper around the imported search_people function to handle None case.
    if search_people is None:
        return []
    # Call the actual function
    return search_people(company, title)

def filter_jobs(matching_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Filter out jobs from blacklisted companies.
    data = json.load(open("users.json"))
    blocklist = data[0].get("blacklist_companies", [])
    blocklist = [company.lower() for company in blocklist]
    filtered = []
    for job in matching_jobs:
        company = job["company_name"].lower()
        if company in blocklist:
            print(f"⚠️ Skipping job from blocked company: {job['company_name']}")
        else:
            filtered.append(job)
    return filtered

def get_user_parameters(interactive: bool = True, args: Optional[argparse.Namespace] = None) -> Dict[str, Any]:
    """Collect run_input parameters from the user via CLI flags or interactive prompts.

    Parameters
    ----------
    interactive: bool
        When True, prompt the user for input. When False, use the provided
        argparse.Namespace (args) to populate values.
    args: argparse.Namespace
        Parsed command line arguments. Only used when interactive is False.

    Returns
    -------
    dict
        A dictionary suitable for use as the run_input to the Apify actor.
    """
    if not interactive and args is None:
        raise ValueError("args must be provided when interactive=False")

    run_input: Dict[str, Any] = {}

    if interactive:
        # Prompt the user for each field with sensible defaults.
        print("\nPlease provide the parameters for your Apify job scrape (leave blank to skip).\n")
        title = input("Job title filter (optional): ").strip()
        location = input("Job location (default: United States): ").strip() or "United States"
        company_names_raw = input("Company names (comma‑separated, optional): ").strip()
        company_ids_raw = input("Company IDs (comma‑separated, optional): ").strip()
        rows_input = input("Number of rows to fetch (default 50): ").strip()
        try:
            rows = int(rows_input) if rows_input else 50
        except ValueError:
            rows = 50
        run_input = {
            "title": title,
            "location": location,
            "companyName": [x.strip() for x in company_names_raw.split(",") if x.strip()] if company_names_raw else [],
            "companyId": [x.strip() for x in company_ids_raw.split(",") if x.strip()] if company_ids_raw else [],
            "publishedAt": "",
            "rows": rows,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        }
    else:
        # Use values supplied on the command line via argparse
        run_input = {
            "title": args.title or "",
            "location": args.location or "United States",
            "companyName": args.company_name or [],
            "companyId": args.company_id or [],
            "publishedAt": "",
            "rows": args.rows,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        }
    # Remove empty string values; Apify will ignore missing keys.
    run_input = {k: v for k, v in run_input.items() if v}
    return run_input


def run_apify_job(apify_token: str, actor_id: str, run_input: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run the specified Apify actor with the provided input and return scraped jobs.

    Parameters
    ----------
    apify_token: str
        A valid Apify API token.
    actor_id: str
        The actor or task identifier to run. This can be a slug like
        "apify/linkedin-jobs-scraper" or a specific actor ID.
    run_input: dict
        The input payload for the actor.

    Returns
    -------
    list
        A list of job dictionaries returned from the actor run.
    """
    if ApifyClient is None:
        raise RuntimeError("apify_client module is not available. Install apify‑client to run this function.")
    client = ApifyClient(apify_token)
    print(f"🚀 Launching Apify actor {actor_id}...")
    run = client.actor(actor_id).call(run_input=run_input)
    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        print("⚠️  Actor run did not produce a dataset. Returning empty job list.")
        return []
    print(f"📥 Fetching results from dataset {dataset_id}...")
    dataset_client = client.dataset(dataset_id)
    jobs: List[Dict[str, Any]] = []
    for item in dataset_client.iterate_items():
        jobs.append(item)
    print(f"✅ Retrieved {len(jobs)} jobs from Apify.")
    return jobs


def save_jobs_to_json(jobs: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
    """Save the scraped jobs into a JSON file with metadata.

    Parameters
    ----------
    jobs: list
        The list of job dictionaries to save.
    output_path: str, optional
        The path of the JSON file. If not supplied, generate one based on the timestamp.

    Returns
    -------
    str
        The path to the JSON file written.
    """
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"apify_jobs_{timestamp}.json"
    data = {
        "metadata": {
            "source": "apify",
            "extracted_at": datetime.now().isoformat(),
            "total_jobs": len(jobs),
        },
        "jobs": jobs,
    }
    with open(output_path, "w", encoding="utf‑8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved jobs to {output_path}")
    return output_path


def init_database(db_path: str) -> None:
    """Initialise the SQLite database and create the jobs table if needed."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Use a simple schema; adapt fields based on the Apify LinkedIn job structure.  Many
    # additional fields could be stored here.  The job_id column is treated as unique.
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            job_title TEXT,
            company_name TEXT,
            location TEXT,
            description_html TEXT,
            poster_name TEXT,
            poster_profile_url TEXT,
            contact_name TEXT,
            contact_email TEXT,
            contact_linkedin TEXT,
            raw_json TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def extract_job_id(job: Dict[str, Any]) -> Optional[str]:
    """Extract a unique identifier for a job.

    LinkedIn jobs scraped by Apify typically include an ID or URL.  This function tries
    multiple keys to find a unique identifier.
    """
    for key in ("id", "jobId", "job_id", "url", "link", "job_url"):
        value = job.get(key)
        if value:
            return str(value)
    return None


def upsert_jobs_into_db(db_path: str, jobs: List[Dict[str, Any]]) -> None:
    """Insert or update job records into the SQLite database.

    Parameters
    ----------
    db_path: str
        Path to the SQLite database file.
    jobs: list
        A list of job dictionaries from Apify.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    inserted = 0
    updated = 0
    for job in jobs:
        job_id = extract_job_id(job)
        if not job_id:
            # Skip any job without an identifier.
            continue
        title = job.get("title") or job.get("job_title") or ""
        company = job.get("companyName") or job.get("company_name") or job.get("company") or ""
        location = job.get("location") or job.get("job_location") or ""
        description_html = job.get("descriptionHtml") or job.get("description_html") or ""
        poster_name = job.get("posterFullName") or job.get("poster_full_name") or job.get("posterName") or ""
        poster_profile_url = job.get("posterProfileUrl") or job.get("poster_profile_url") or job.get("posterUrl") or ""
        raw_json_str = json.dumps(job, ensure_ascii=False)
        # Upsert logic: try update, if rowcount==0 insert.
        c.execute(
            """
            UPDATE jobs
            SET job_title=?, company_name=?, location=?, description_html=?,
                poster_name=?, poster_profile_url=?, raw_json=?
            WHERE job_id=?
            """,
            (title, company, location, description_html, poster_name, poster_profile_url, raw_json_str, job_id),
        )
        if c.rowcount == 0:
            c.execute(
                """
                INSERT INTO jobs (job_id, job_title, company_name, location, description_html,
                                  poster_name, poster_profile_url, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, title, company, location, description_html, poster_name, poster_profile_url, raw_json_str),
            )
            inserted += 1
        else:
            updated += 1
    conn.commit()
    conn.close()
    print(f"📂 Database upsert complete: {inserted} inserted, {updated} updated.")


def enrich_contacts(db_path: str) -> None:
    """Enrich job entries in the database with recruiter contact info via Apollo.

    For each job record where the poster_name or poster_profile_url is missing, this
    function queries Apollo using the company and job title to find recruiters.  It
    chooses the first contact returned and updates the contact columns.  If
    `search_people` is unavailable (due to missing API key or import failure), the
    function logs a message and does nothing.
    """
    if search_people is None:
        print("ℹ️  Apollo enrichment skipped: search_people function not available.")
        return
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """SELECT job_id, company_name, job_title, poster_name, poster_profile_url, contact_name
           FROM jobs"""
    )
    rows = c.fetchall()
    updated_count = 0
    for row in rows:
        job_id, company, title, poster_name, poster_profile_url, contact_name = row
        # Skip if we already have contact info or if poster info exists.
        if contact_name:
            continue
        if poster_name and poster_profile_url:
            # If the job posting already includes poster info, use that as contact.
            c.execute(
                """
                UPDATE jobs
                SET contact_name=?, contact_email=?, contact_linkedin=?
                WHERE job_id=?
                """,
                (poster_name, None, poster_profile_url, job_id),
            )
            updated_count += 1
            continue
        # Otherwise, call Apollo to find recruiters.  This may return multiple contacts;
        # we choose the first.
        try:
            contacts = look_people(company, title)
        except Exception as exc:
            print(f"⚠️  Apollo search failed for {company}/{title}: {exc}")
            contacts = []
        if not contacts:
            continue
        contact = contacts[0]
        c.execute(
            """
            UPDATE jobs
            SET contact_name=?, contact_email=?, contact_linkedin=?
            WHERE job_id=?
            """,
            (contact.get("name"), contact.get("email"), contact.get("linkedin_url"), job_id),
        )
        updated_count += 1
    conn.commit()
    conn.close()
    print(f"📧 Enriched contact info for {updated_count} job(s).")


def extract_resume_text(resume_path: str) -> str:
    """Extract plain text from a resume file.

    This function supports simple text extraction from .txt, .md, .pdf and .docx files.
    For PDF and DOCX files, only basic extraction is attempted using third‑party
    libraries.  If extraction fails, an empty string is returned.
    """
    if not os.path.isfile(resume_path):
        print(f"⚠️  Resume file not found: {resume_path}")
        return ""
    ext = os.path.splitext(resume_path)[1].lower()
    try:
        if ext in {".txt", ".md"}:
            with open(resume_path, encoding="utf‑8", errors="ignore") as f:
                return f.read()
        elif ext == ".pdf":
            try:
                import pdfminer.high_level
                text = pdfminer.high_level.extract_text(resume_path)
                return text
            except Exception as e:
                print(f"⚠️  PDF extraction failed: {e}")
                return ""
        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(resume_path)
                return "\n".join([p.text for p in doc.paragraphs])
            except Exception as e:
                print(f"⚠️  DOCX extraction failed: {e}")
                return ""
        else:
            print(f"⚠️  Unsupported resume format: {ext}")
            return ""
    except Exception as e:
        print(f"⚠️  Resume extraction error: {e}")
        return ""


def clean_html(raw_html: str) -> str:
    """Remove HTML tags from a string using a simple regex."""
    if not raw_html:
        return ""
    # Remove script/style tags and their contents first
    cleaned = re.sub(r"<script.*?>.*?</script>", "", raw_html, flags=re.S)
    cleaned = re.sub(r"<style.*?>.*?</style>", "", cleaned, flags=re.S)
    # Remove all other tags
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def analyze_job_match_with_openai(resume_text: str, job_description: str, job_title: str, company_name: str, job_id: str, openai_api_key: str) -> Dict[str, Any]:
    """Use OpenAI to analyze job matching and return structured JSON with matching/missing criteria.
    
    Parameters
    ----------
    resume_text: str
        Candidate's resume content
    job_description: str
        Job description to analyze against
    job_title: str
        Job title
    company_name: str
        Company name
    job_id: str
        Unique job identifier
    openai_api_key: str
        OpenAI API key
        
    Returns
    -------
    dict
        Structured JSON with matching analysis
    """
    if not openai or not openai_api_key:
        print("⚠️  OpenAI not available, using fallback matching")
        return {
            "job_id": job_id,
            "job_title": job_title,
            "company_name": company_name,
            "analysis": {
                "overall_match_score": 50,
                "match_threshold_met": False,
                "matching_criteria": {"skills": [], "experience": [], "education": [], "tools": []},
                "missing_criteria": {"skills": [], "experience": [], "certifications": [], "domain_knowledge": []},
                "recommendations": {"resume_updates": [], "keywords_to_add": [], "sections_to_enhance": []}
            }
        }
    
    try:
        client = openai.OpenAI(api_key=openai_api_key)
        
        prompt = f"""
Analyze the job match between this resume and job description. Return a JSON response with the exact structure below:

Job Title: {job_title}
Company: {company_name}
Job ID: {job_id}

Job Description:
{job_description}

Candidate Resume:
{resume_text}

Return ONLY a valid JSON object with this exact structure:
{{
  "job_id": "{job_id}",
  "job_title": "{job_title}",
  "company_name": "{company_name}",
  "analysis": {{
    "overall_match_score": <number 0-100>,
    "match_threshold_met": <boolean - true if score >= >,
    "matching_criteria": {{
      "skills": ["list of matching technical skills"],
      "experience": ["list of matching experience areas"],
      "education": ["list of matching education requirements"],
      "tools": ["list of matching tools/technologies"]
    }},
    "missing_criteria": {{
      "skills": ["list of missing technical skills"],
      "experience": ["list of missing experience areas"],
      "certifications": ["list of missing certifications"],
      "domain_knowledge": ["list of missing domain expertise"]
    }},
    "recommendations": {{
      "resume_updates": ["specific suggestions for resume improvements"],
      "keywords_to_add": ["important keywords to incorporate"],
      "sections_to_enhance": ["resume sections that need improvement"]
    }}
  }}
}}
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert ATS and resume matching analyst. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.2
        )
        
        result_text = response.choices[0].message.content.strip()
        # Parse JSON response
        try:
            result_json = json.loads(result_text)
            return result_json
        except json.JSONDecodeError:
            print(f"⚠️  Failed to parse OpenAI JSON response: {result_text[:200]}...")
            return {
                "job_id": job_id,
                "job_title": job_title,
                "company_name": company_name,
                "analysis": {
                    "overall_match_score": 50,
                    "match_threshold_met": False,
                    "matching_criteria": {"skills": [], "experience": [], "education": [], "tools": []},
                    "missing_criteria": {"skills": [], "experience": [], "certifications": [], "domain_knowledge": []},
                    "recommendations": {"resume_updates": [], "keywords_to_add": [], "sections_to_enhance": []}
                }
            }
        
    except Exception as e:
        print(f"⚠️  OpenAI job matching analysis failed: {e}")
        return {
            "job_id": job_id,
            "job_title": job_title,
            "company_name": company_name,
            "analysis": {
                "overall_match_score": 50,
                "match_threshold_met": False,
                "matching_criteria": {"skills": [], "experience": [], "education": [], "tools": []},
                "missing_criteria": {"skills": [], "experience": [], "certifications": [], "domain_knowledge": []},
                "recommendations": {"resume_updates": [], "keywords_to_add": [], "sections_to_enhance": []}
            }
        }


def similarity_score(resume_text: str, job_description: str) -> float:
    """Compute a similarity ratio between two strings using SequenceMatcher."""
    if not resume_text or not job_description:
        return 0.0
    return SequenceMatcher(None, resume_text.lower(), job_description.lower()).ratio()


def select_matching_jobs_with_openai(db_path: str, resume_text: str, openai_api_key: str, threshold: float = 40.0) -> List[Dict[str, Any]]:
    """Use OpenAI to analyze job matching and return detailed analysis for each job.

    Returns a list of job analysis dictionaries with matching details.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT job_id, company_name, job_title, description_html FROM jobs")
    matches: List[Dict[str, Any]] = []
    
    for job_id, company, title, desc_html in c.fetchall():
        plain_desc = clean_html(desc_html or "")
        
        # Use OpenAI to analyze job matching
        analysis = analyze_job_match_with_openai(
            resume_text, plain_desc, title, company, job_id, openai_api_key
        )
        
        # Check if match threshold is met
        if analysis["analysis"]["match_threshold_met"]:
            matches.append(analysis)
            
        # Save analysis to JSON file
        analysis_filename = f"job_analysis_{job_id}.json"
        try:
            with open(analysis_filename, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            print(f"📊 Saved job analysis: {analysis_filename} (Score: {analysis['analysis']['overall_match_score']}%)")
        except Exception as e:
            print(f"⚠️  Failed to save analysis for job {job_id}: {e}")
    
    conn.close()
    print(f"🔍 Found {len(matches)} job(s) matching resume with OpenAI analysis (threshold: {threshold}%)")
    return matches


def select_matching_jobs(db_path: str, resume_text: str, threshold: float = 0.6) -> List[Tuple[str, str]]:
    """Select job IDs and descriptions that match the resume above a threshold.

    Returns a list of tuples (job_id, company_name) for matching jobs.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT job_id, company_name, job_title, description_html FROM jobs")
    matches: List[Tuple[str, str]] = []
    for job_id, company, title, desc_html in c.fetchall():
        plain_desc = clean_html(desc_html or "")
        score = similarity_score(resume_text, plain_desc)
        if score >= threshold:
            matches.append((job_id, company))
    conn.close()
    print(f"🔍 Found {len(matches)} job(s) matching resume with threshold {threshold:.2f}")
    return matches


def generate_ats_optimized_resume_with_analysis(resume_text: str, job_analysis: Dict[str, Any], openai_api_key: str) -> str:
    """Generate ATS-optimized resume using detailed job matching analysis.
    
    Parameters
    ----------
    resume_text: str
        Original resume content
    job_analysis: dict
        Detailed job matching analysis from OpenAI
    openai_api_key: str
        OpenAI API key
        
    Returns
    -------
    str
        ATS-optimized resume content
    """
    if not openai or not openai_api_key:
        print("⚠️  OpenAI not available, using fallback resume generation")
        return generate_modified_resume_fallback(resume_text, "")
    
    try:
        client = openai.OpenAI(api_key=openai_api_key)
        
        analysis = job_analysis["analysis"]
        job_title = job_analysis["job_title"]
        company_name = job_analysis["company_name"]
        
        prompt = f"""
Optimize this resume for ATS and job matching using the detailed analysis provided:

Job: {job_title} at {company_name}
Match Score: {analysis['overall_match_score']}%

MATCHING CRITERIA (keep and emphasize):
Skills: {', '.join(analysis['matching_criteria']['skills'])}
Experience: {', '.join(analysis['matching_criteria']['experience'])}
Education: {', '.join(analysis['matching_criteria']['education'])}
Tools: {', '.join(analysis['matching_criteria']['tools'])}

MISSING CRITERIA (add if possible):
Skills: {', '.join(analysis['missing_criteria']['skills'])}
Experience: {', '.join(analysis['missing_criteria']['experience'])}
Certifications: {', '.join(analysis['missing_criteria']['certifications'])}
Domain Knowledge: {', '.join(analysis['missing_criteria']['domain_knowledge'])}

RECOMMENDATIONS:
{chr(10).join(analysis['recommendations']['resume_updates'])}

Keywords to add: {', '.join(analysis['recommendations']['keywords_to_add'])}

Original Resume:
{resume_text}

Instructions:
1. Achieve >95% ATS compatibility and >95% job match
2. Incorporate missing skills/keywords naturally
3. Emphasize matching criteria more prominently
4. Add recommended keywords throughout
5. Enhance sections: {', '.join(analysis['recommendations']['sections_to_enhance'])}
6. Maintain professional flow and readability
7. Keep all original achievements but reframe for this role

Return only the optimized resume content.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert ATS resume optimizer specializing in achieving 95%+ match scores."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        optimized_resume = response.choices[0].message.content.strip()
        return optimized_resume
        
    except Exception as e:
        print(f"⚠️  OpenAI resume optimization failed: {e}")
        return generate_modified_resume_fallback(resume_text, "")


def generate_ats_optimized_resume(resume_text: str, job_description: str, job_title: str, company_name: str, openai_api_key: str) -> str:
    """Generate ATS-optimized resume using OpenAI API to achieve >95% match and ATS score.
    
    Parameters
    ----------
    resume_text: str
        Original resume content
    job_description: str
        Job description to optimize against
    job_title: str
        Job title for context
    company_name: str
        Company name for context
    openai_api_key: str
        OpenAI API key
        
    Returns
    -------
    str
        ATS-optimized resume content
    """
    if not openai or not openai_api_key:
        print("⚠️  OpenAI not available, using fallback resume generation")
        return generate_modified_resume_fallback(resume_text, job_description)
    
    try:
        client = openai.OpenAI(api_key=openai_api_key)
        
        prompt = f"""
You are an expert ATS (Applicant Tracking System) resume optimizer. Your task is to modify the provided resume to achieve:
1. >95% job match score
2. >95% ATS compatibility score

Job Title: {job_title}
Company: {company_name}

Job Description:
{job_description}

Original Resume:
{resume_text}

Instructions:
1. Rewrite the resume to maximize keyword matching with the job description
2. Use exact keywords and phrases from the job description
3. Maintain ATS-friendly formatting (simple structure, standard headings)
4. Keep all original achievements but reframe them to match job requirements
5. Add relevant skills mentioned in job description if missing
6. Optimize the professional summary to mirror job requirements
7. Use action verbs and quantifiable achievements
8. Ensure the resume flows naturally and doesn't appear keyword-stuffed

Return only the optimized resume content, no additional commentary.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert resume writer specializing in ATS optimization."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        optimized_resume = response.choices[0].message.content.strip()
        return optimized_resume
        
    except Exception as e:
        print(f"⚠️  OpenAI resume optimization failed: {e}")
        return generate_modified_resume_fallback(resume_text, job_description)


def generate_modified_resume_fallback(resume_text: str, job_description: str) -> str:
    """Fallback resume modification when OpenAI is not available."""
    try:
        from collections import Counter
        words = re.findall(r"[A-Za-z]{3,}", job_description.lower())
        # Filter out common stop words
        stopwords = {
            "and", "the", "for", "with", "from", "that", "this", "will", "you",
            "your", "our", "are", "job", "role", "team", "who", "have", "has",
        }
        keywords = [w for w in words if w not in stopwords]
        most_common = [w for w, _ in Counter(keywords).most_common(10)]
        if most_common:
            skills_section = "\n\nRelevant Keywords for this role:\n" + ", ".join(most_common)
            return resume_text.strip() + skills_section
        else:
            return resume_text
    except Exception:
        return resume_text


def generate_optimized_cover_letter(job_title: str, company_name: str, recruiter_name: str, job_description: str, resume_text: str, openai_api_key: str) -> str:
    """Generate an optimized cover letter using OpenAI API.
    
    Parameters
    ----------
    job_title: str
        Job title
    company_name: str
        Company name
    recruiter_name: str
        Recruiter name
    job_description: str
        Job description for context
    resume_text: str
        Resume content for alignment
    openai_api_key: str
        OpenAI API key
        
    Returns
    -------
    str
        Optimized cover letter content
    """
    if not openai or not openai_api_key:
        print("⚠️  OpenAI not available, using fallback cover letter generation")
        return generate_cover_letter_fallback(job_title, company_name, recruiter_name)
    
    try:
        client = openai.OpenAI(api_key=openai_api_key)
        
        prompt = f"""
Write a compelling, personalized cover letter for email application:

Job Title: {job_title}
Company: {company_name}
Recruiter: {recruiter_name or 'Hiring Manager'}

Job Description:
{job_description}

Candidate's Resume Summary:
{resume_text[:1000]}...

Instructions:
1. Format for email body (no address headers or placeholders)
2. Start directly with "Dear [Name],"
3. Create professional, engaging content
4. Highlight specific qualifications matching job requirements
5. Use keywords from job description naturally
6. Show enthusiasm for role and company
7. Include specific examples of relevant achievements
8. Keep concise (3-4 paragraphs)
9. End with professional closing and candidate's actual name
10. NO placeholder text like [Your Address], [Date], etc.
11. Use real contact information from resume when available

Return only the email-ready cover letter content.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert career counselor and cover letter writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.4
        )
        
        cover_letter = response.choices[0].message.content.strip()
        return cover_letter
        
    except Exception as e:
        print(f"⚠️  OpenAI cover letter generation failed: {e}")
        return generate_cover_letter_fallback(job_title, company_name, recruiter_name)


def generate_cover_letter_fallback(job_title: str, company_name: str, recruiter_name: str) -> str:
    """Fallback cover letter generation when OpenAI is not available."""
    return (
        f"Dear {recruiter_name or 'Recruiter'},\n\n"
        f"I hope this message finds you well. I recently came across the {job_title} position "
        f"at {company_name} and was excited by the opportunity. My background and skills "
        f"align closely with the requirements listed, and I have attached a tailored version of my resume "
        f"for your consideration. I would welcome the chance to discuss how my experience could "
        f"benefit {company_name}.\n\n"
        "Thank you for your time and consideration.\n\n"
        "Sincerely,\nYour Name"
    )


def send_email_via_sendgrid(
    sendgrid_api_key: str,
    to_email: str,
    subject: str,
    content: str,
    resume_text: str,
    dry_run: bool = False,
) -> None:
    """Send an email using SendGrid with optimized resume and cover letter.

    Parameters
    ----------
    sendgrid_api_key: str
        The API key for SendGrid.
    to_email: str
        Recipient email address.
    subject: str
        The subject of the email.
    content: str
        The body of the email (optimized cover letter).
    resume_text: str
        The contents of the optimized resume to attach.
    dry_run: bool
        If True, skip sending and just log the request.
    """
    # Lazy import to avoid circular dependency
    try:
        from app.core.config import settings as _settings
        from_email = _settings.SENDGRID_FROM_EMAIL or "noreply@example.com"
        from_name = _settings.SENDGRID_FROM_NAME or "Recruitment Bot"
        sandbox_flag = _settings.SENDGRID_SANDBOX
    except Exception:  # noqa: BLE001
        from_email = "noreply@example.com"
        from_name = "Recruitment Bot"
        sandbox_flag = None

    import base64
    encoded_resume = base64.b64encode((resume_text or "").encode("utf-8")).decode("utf-8")

    mail_settings = {}
    if sandbox_flag is True:
        mail_settings = {"mail_settings": {"sandbox_mode": {"enable": True}}}

    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject,
            }
        ],
        "from": {"email": from_email, "name": from_name},
        "content": [
            {
                "type": "text/plain",
                "value": content,
            }
        ],
        "attachments": [
            {
                "content": encoded_resume,
                "type": "text/plain",
                "filename": "resume.txt",
                "disposition": "attachment",
            }
        ],
        **mail_settings,
    }
    if dry_run:
        print(f"(Dry run) Would send email to {to_email} with subject '{subject}'.")
        return
    try:
        import requests
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Email sent to {to_email}")
        else:
            print(f"⚠️  Failed to send email to {to_email}: {response.status_code} {response.text[:200]}")
    except Exception as e:
        print(f"⚠️  Error sending email: {e}")


def main() -> None:
    """Command‑line entry point for the pipeline."""
    global os, subprocess, sys  # Ensure these modules are accessible

    parser = argparse.ArgumentParser(description="Automate LinkedIn job scraping and applications.")
    parser.add_argument("--actor-id", type=str, default="BHzefUZlZRKWxkTck", help="Apify actor ID or slug")
    parser.add_argument("--title", type=str, default="", help="Job title filter")
    parser.add_argument("--location", type=str, default="United States", help="Job location filter")
    parser.add_argument("--company-name", action="append", help="Company name (can specify multiple)")
    parser.add_argument("--company-id", action="append", help="Company ID (can specify multiple)")
    parser.add_argument("--rows", type=int, default=50, help="Number of job rows to fetch")
    parser.add_argument("--resume", type=str, help="Path to your resume file (txt, md, pdf, docx)")
    parser.add_argument("--database", type=str, default="jobs.db", help="SQLite database file path")
    parser.add_argument("--output-json", type=str, help="Path to save scraped jobs JSON")
    parser.add_argument("--threshold", type=float, default=30.0, help="Resume match threshold (0-100 for OpenAI analysis)")
    parser.add_argument("--dry-run", action="store_true", help="Skip sending emails, just log actions")
    parser.add_argument("--interactive", action="store_true", help="Collect input via interactive prompts")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    apify_token = os.getenv("APIFY_TOKEN", "").strip()
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    # Apollo API key is loaded implicitly in apollotest via environment variable
    if not apify_token:
        raise SystemExit("APIFY_TOKEN environment variable not set. Exiting.")

    # Step 1: Get run_input
    run_input = get_user_parameters(interactive=args.interactive, args=args)

    # Step 2: Run Apify actor and fetch jobs
    jobs = run_apify_job(apify_token, args.actor_id, run_input)
    if not jobs:
        print("No jobs retrieved. Nothing further to do.")
        return

    # Step 3: Save jobs to JSON
    json_path = save_jobs_to_json(jobs, args.output_json)

    # Step 4: Initialise and update the database
    init_database(args.database)
    upsert_jobs_into_db(args.database, jobs)

    # Step 5: Enrich contact information
    enrich_contacts(args.database)

    # Step 6: Read resume and match jobs using OpenAI analysis
    if args.resume:
        resume_text = extract_resume_text(args.resume)
        if resume_text:
            # Use OpenAI-based matching with detailed analysis
            matching_jobs = select_matching_jobs_with_openai(args.database, resume_text, openai_api_key)
            
            # use filter to remove companies which are in blocklist
            filtered_jobs = filter_jobs(matching_jobs)

            # Step 7: For each matching job, use analysis to optimize resume and send email
            if filtered_jobs and sendgrid_api_key:
                conn = sqlite3.connect(args.database)
                c = conn.cursor()

                for job_analysis in filtered_jobs:
                    job_id = job_analysis["job_id"]
                    job_title = job_analysis["job_title"]
                    company_name = job_analysis["company_name"]
                    
                    # Fetch contact info
                    c.execute(
                        "SELECT contact_name, contact_email, description_html"
                        " FROM jobs WHERE job_id=?",
                        (job_id,),
                    )
                    row = c.fetchone()
                    if not row:
                        continue
                    contact_name, contact_email, desc_html = row
                    if not contact_email:
                        print(f"⚠️  No email available for job {job_id}; skipping email.")
                        continue
                    
                    # Generate ATS-optimized resume using detailed analysis
                    optimized_resume = generate_ats_optimized_resume_with_analysis(
                        resume_text, job_analysis, openai_api_key
                    )
                    
                    # Generate optimized cover letter
                    plain_job_desc = clean_html(desc_html or "")
                    optimized_cover_letter = generate_optimized_cover_letter(
                        job_title, company_name, contact_name, plain_job_desc, resume_text, openai_api_key
                    )
                    
                    # Save optimized resume and cover letter with job ID
                    resume_filename = f"resume_{job_id}.txt"
                    cover_letter_filename = f"cover_letter_{job_id}.txt"
                    
                    try:
                        with open(resume_filename, "w", encoding="utf-8") as f:
                            f.write(optimized_resume)

                        # Convert to DOCX format
                        convert_resume(resume_filename, resume_filename.replace(".txt", ".docx"))
                        print(f"💾 Saved optimized resume: {resume_filename}")

                        with open(cover_letter_filename, "w", encoding="utf-8") as f:
                            f.write(optimized_cover_letter)

                        # Convert to DOCX format
                        convert_cover_letter(cover_letter_filename, cover_letter_filename.replace(".txt", ".docx"))
                        print(f"💾 Saved optimized cover letter: {cover_letter_filename}")

                    except Exception as e:
                        print(f"⚠️  Failed to save files for job {job_id}: {e}")
                    
                    subject = f"Application for {job_title} at {company_name}"
                    send_email_via_sendgrid(
                        sendgrid_api_key,
                        contact_email,
                        subject,
                        optimized_cover_letter,
                        optimized_resume,
                        dry_run=args.dry_run,
                    )
                conn.close()
            elif filtered_jobs and not sendgrid_api_key:
                print("SENDGRID_API_KEY is not set; cannot send emails. Use --dry-run to preview.")
        else:
            print("Resume text is empty; skipping job matching and emailing.")
    else:
        print("Resume not provided; skipping job matching and emailing.")

    print("\nPipeline completed.")

    # Launch email tracker after pipeline completion
    try:
        import subprocess
        import sys
        import os
        
        tracker_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                     "email_tracker_all_in_one.py")
        
        if os.path.exists(tracker_script):
            # Create log file for tracker output
            log_file = open("email_tracker.log", "a")
            
            # Launch the email tracker as a detached process
            tracker_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "email_tracker_all_in_one:app", "--port", "8001"],
                stdout=log_file,
                stderr=log_file,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                start_new_session=True  # Detach the process
            )
            
            print(f"📧 Email tracker started (PID: {tracker_process.pid})")
        else:
            print("⚠️ Email tracker script not found at:", tracker_script)
    except Exception as e:
        print(f"⚠️ Failed to start email tracker: {e}")


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class PipelineRequest(BaseModel):
    actor_id: str = "BHzefUZlZRKWxkTck"
    title: str = ""
    location: str = "United States"
    company_name: list[str] = []
    company_id: list[str] = []
    rows: int = 50
    resume: str = ""
    database: str = "jobs.db"
    output_json: str = ""
    threshold: float = 30.0
    dry_run: bool = False
    interactive: bool = False

class PipelineResponse(BaseModel):
    jobs_scraped: int
    jobs_matched: int
    emails_sent: int
    message: str

@app.post("/run-pipeline", response_model=PipelineResponse)
def run_pipeline_api(request: PipelineRequest):
    # ...parse environment variables...
    load_dotenv()
    apify_token = os.getenv("APIFY_TOKEN", "").strip()
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not apify_token:
        raise HTTPException(status_code=400, detail="APIFY_TOKEN environment variable not set.")

    # Step 1: Get run_input
    run_input = {
        "title": request.title or "",
        "location": request.location or "United States",
        "companyName": request.company_name or [],
        "companyId": request.company_id or [],
        "publishedAt": "",
        "rows": request.rows,
        "proxy": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
    }
    run_input = {k: v for k, v in run_input.items() if v}

    # Step 2: Run Apify actor and fetch jobs
    jobs = run_apify_job(apify_token, request.actor_id, run_input)
    if not jobs:
        return PipelineResponse(jobs_scraped=0, jobs_matched=0, emails_sent=0, message="No jobs retrieved.")

    # Step 3: Save jobs to JSON
    json_path = save_jobs_to_json(jobs, request.output_json)

    # Step 4: Initialise and update the database
    init_database(request.database)
    upsert_jobs_into_db(request.database, jobs)

    # Step 5: Enrich contact information
    enrich_contacts(request.database)

    jobs_matched = 0
    emails_sent = 0

    # Step 6: Read resume and match jobs using OpenAI analysis
    if request.resume:
        resume_text = extract_resume_text(request.resume)
        if resume_text:
            matching_jobs = select_matching_jobs_with_openai(request.database, resume_text, openai_api_key)
            filtered_jobs = filter_jobs(matching_jobs)
            jobs_matched = len(filtered_jobs)
            if filtered_jobs and sendgrid_api_key:
                conn = sqlite3.connect(request.database)
                c = conn.cursor()
                for job_analysis in filtered_jobs:
                    job_id = job_analysis["job_id"]
                    job_title = job_analysis["job_title"]
                    company_name = job_analysis["company_name"]
                    c.execute(
                        "SELECT contact_name, contact_email, description_html FROM jobs WHERE job_id=?",
                        (job_id,),
                    )
                    row = c.fetchone()
                    if not row:
                        continue
                    contact_name, contact_email, desc_html = row
                    if not contact_email:
                        continue
                    optimized_resume = generate_ats_optimized_resume_with_analysis(
                        resume_text, job_analysis, openai_api_key
                    )
                    plain_job_desc = clean_html(desc_html or "")
                    optimized_cover_letter = generate_optimized_cover_letter(
                        job_title, company_name, contact_name, plain_job_desc, resume_text, openai_api_key
                    )
                    subject = f"Application for {job_title} at {company_name}"
                    send_email_via_sendgrid(
                        sendgrid_api_key,
                        contact_email,
                        subject,
                        optimized_cover_letter,
                        optimized_resume,
                        dry_run=request.dry_run,
                    )
                    emails_sent += 1
                conn.close()
            elif filtered_jobs and not sendgrid_api_key:
                pass  # No emails sent
        else:
            return PipelineResponse(
                jobs_scraped=len(jobs),
                jobs_matched=0,
                emails_sent=0,
                message="Resume text is empty; skipping job matching and emailing."
            )
    else:
        return PipelineResponse(
            jobs_scraped=len(jobs),
            jobs_matched=0,
            emails_sent=0,
            message="Resume not provided; skipping job matching and emailing."
        )

    return PipelineResponse(
        jobs_scraped=len(jobs),
        jobs_matched=jobs_matched,
        emails_sent=emails_sent,
        message="Pipeline completed."
    )


# No changes needed; this script does not use SQLAlchemy.


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "fastapi":
        uvicorn.run("job_application_pipeline:app", host="0.0.0.0", port=8000, reload=False)
    else:
        main()
