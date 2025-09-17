from dotenv import load_dotenv
load_dotenv()

import os
import re
import json
import requests
from typing import List, Dict, Any, Tuple

APOLLO_BASE = "https://api.apollo.io/api/v1"
API_KEY = os.getenv("APOLLO_API_KEY", "").strip()
if not API_KEY:
    raise SystemExit("❌  APOLLO_API_KEY missing")

HEADERS = {
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "X-Api-Key": API_KEY
}

BASE_RECRUITER_TITLES = [
    "recruiter", "technical recruiter", "talent acquisition", "sourcer", "hiring manager"
]

RECRUITER_KEYWORDS = re.compile(
    r"\b(recruit|talent|sourc|staffing|people\s*&?\s*culture|people ops|human\s+resources|hr|ta)\b",
    re.IGNORECASE
)

STOPWORDS = {
    "the","a","an","and","or","of","for","to","in","on","at","by","with","from",
    "ii","iii","iv","v","i","x","l","llc","inc","co","corp","company",
    "remote","hybrid","contract","full","part","time","fulltime","parttime",
    "sr","jr","senior","junior","lead","principal","staff","manager","director","head",
    "vp","chief","intern","internship","entry","mid","associate",
    "seasonal","temporary","temp",
    "usa","united","states"
}

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-\+\.]*")
MAX_RESULTS = 5


def _search(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        r = requests.get(f"{APOLLO_BASE}/people/search",
                         headers=HEADERS, params=params, timeout=30)
        if r.status_code != 200:
            print(f"⚠️  Search HTTP {r.status_code}: {r.text[:200]}")
        r.raise_for_status()
        people = r.json().get("people", [])
        if not people:
            # Light params echo for debug
            echo = {k: params[k] for k in ("q_organization_name", "person_locations[]") if k in params}
            print("ℹ️  Search returned 0 people for:", echo)
        return people
    except Exception as e:
        print(f"⚠️  Search error: {e}")
        return []


def _unlock_email(person_id: str) -> str:
    """Return real e-mail or empty string."""
    payload = {"api_key": API_KEY, "id": person_id, "reveal_email": True}
    try:
        r = requests.post(f"{APOLLO_BASE}/people/match",
                          json=payload, headers=HEADERS, timeout=30)
        if r.status_code == 402:
            
            return ""
        if r.status_code != 200:
            print(f"ℹ️  Email unlock HTTP {r.status_code} for {person_id}: {r.text[:120]}")
            return ""
        return r.json().get("person", {}).get("email") or ""
    except Exception as e:
        print(f"ℹ️  Email unlock error for {person_id}: {e}")
        return ""


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _tokens_from_title(title: str) -> List[str]:
    """Tokenize, lowercase, drop stopwords & pure numbers, keep order & de-dupe."""
    t = _norm(title)
    tokens = [w.lower() for w in TOKEN_RE.findall(t)]
    cleaned = []
    for w in tokens:
        w = w.strip(".+-")
        if not w or w in STOPWORDS:
            continue
        if w.isdigit():
            continue
        cleaned.append(w)
    
    seen, out = set(), []
    for w in cleaned:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def _bigrams(words: List[str]) -> List[str]:
    out = []
    for i in range(len(words) - 1):
        out.append(f"{words[i]} {words[i+1]}")
    
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _phrases_from_title(title: str) -> List[str]:
    """Use bigrams first (more specific), then tokens; trimmed to keep API params sane."""
    toks = _tokens_from_title(title)
    bgs = _bigrams(toks)
    phrases = bgs + toks
    return phrases[:25]


def _build_dynamic_recruiter_titles(job_title: str) -> List[str]:
    """
    From derived phrases, produce recruiter titles like:
      "<phrase> recruiter", "<phrase> sourcer", "<phrase> talent acquisition", "<phrase> hiring manager"
    Also append a minimal fallback set.
    """
    phrases = _phrases_from_title(job_title)
    dynamic: List[str] = []
    for p in phrases:
        dynamic.extend([
            f"{p} recruiter",
            f"{p} sourcer",
            f"{p} talent acquisition",
            f"{p} hiring manager",
        ])
    dynamic.extend(BASE_RECRUITER_TITLES)

    
    seen, final = set(), []
    for t in dynamic:
        key = t.lower()
        if key and key not in seen:
            seen.add(key)
            final.append(t)
    return final[:100]



def _title_is_recruiting(title: str, phrases: List[str]) -> bool:
    """
    True if title looks like recruiting/TA/HR and (preferably) contains one of our phrases.
    Allow generic recruiter/TA titles even without phrase hit.
    """
    t = _norm(title)
    if not t or not RECRUITER_KEYWORDS.search(t):
        return False
    for p in phrases:
        pp = _norm(p)
        if pp and pp in t:
            return True
    return ("recruiter" in t) or ("talent acquisition" in t) or ("sourc" in t) or ("hiring manager" in t)


def _filter_and_rank_people(people: List[Dict[str, Any]], phrases: List[str]) -> List[Dict[str, str]]:
    SENIORITY_SCORES = {
        "principal": 6, "director": 6, "head": 6, "vp": 6, "lead": 5,
        "senior": 4, "manager": 4, "partner": 4, "specialist": 3,
        "coordinator": 2, "recruiter": 5, "sourcer": 4, "hr": 3
    }
    cleaned = []
    for p in people or []:
        title = p.get("title") or p.get("person_title") or ""
        if not _title_is_recruiting(title, phrases):
            continue
        name = (f"{p.get('first_name','')} {p.get('last_name','')}".strip()
                or p.get("name","").strip())
        cleaned.append({
            "name": name,
            "title": title,
            "linkedin_url": p.get("linkedin_url") or p.get("person_linkedin_url") or "",
            "id": p.get("id","")
        })

    def score_title(t: str) -> int:
        t = _norm(t)
        score = 0
        if RECRUITER_KEYWORDS.search(t):
            score += 5
        for k, v in SENIORITY_SCORES.items():
            if k in t:
                score += v
        for ph in phrases:
            ph = _norm(ph)
            if ph and ph in t:
                score += 3
        if "talent acquisition" in t: score += 3
        if "recruit" in t: score += 3
        if "sourc" in t: score += 2
        return score

    cleaned.sort(key=lambda x: score_title(x["title"]), reverse=True)
    return cleaned



def search_people(company: str, job_title: str) -> List[Dict[str, str]]:
    phrases = _phrases_from_title(job_title)
    dynamic_titles = _build_dynamic_recruiter_titles(job_title)

    
    p1 = _search({
        "q_organization_name": company,
        "person_titles[]": dynamic_titles,
        "page": 1,
        "per_page": 100,
        "person_locations[]": "United States",
    })
    best = _filter_and_rank_people(p1, phrases)

    if not best:
        
        p2 = _search({
            "q_organization_name": company,
            "page": 1,
            "per_page": 100,
            "person_locations[]": "United States",
        })
        best = _filter_and_rank_people(p2, phrases)

    
    out: List[Dict[str, str]] = []
    for p in best[:MAX_RESULTS]:
        email = _unlock_email(p.get("id", "")) or "email_not_unlocked@domain.com"
        out.append({
            "name": p["name"],
            "title": p["title"],
            "email": email,
            "linkedin_url": p.get("linkedin_url", "")
        })

    print(f"📊  {company} ({job_title}) → {len(out)} contacts (phrases: {', '.join(phrases) or '—'})")
    return out



def _load_jobs() -> Tuple[list, dict | None]:
    """
    Returns (job_list, wrapper_dict_or_None).
    If jobs.json is wrapped ({"jobs":[...]}), returns (list, wrapper_dict).
    If it's a plain list, returns (list, None).
    """
    with open("jobs.json", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "jobs" in data and isinstance(data["jobs"], list):
        return data["jobs"], data  # wrapped
    elif isinstance(data, list):
        return data, None  # plain list
    else:
        raise SystemExit("❌ jobs.json format not recognized. Expected a list or a dict with a 'jobs' list.")


def _save_jobs(job_list: list, wrapper: dict | None):
    if wrapper is not None:
        wrapper["jobs"] = job_list
        with open("jobs.json", "w", encoding="utf-8") as f:
            json.dump(wrapper, f, indent=2, ensure_ascii=False)
    else:
        with open("jobs.json", "w", encoding="utf-8") as f:
            json.dump(job_list, f, indent=2, ensure_ascii=False)



def main():
    jobs, wrapper = _load_jobs()

    if not jobs:
        print("⚠️  jobs.json contains 0 jobs.")
        return

    updated = 0
    for job in jobs:
        if not isinstance(job, dict):
            print("⚠️  Skipping non-dict job entry:", job)
            continue

        
        company = (job.get("company") or job.get("company_name") or "").strip()
        title   = (job.get("title") or job.get("job_title") or "").strip()

        if not company or not title:
            job["recruiters"] = []
            continue

        job["recruiters"] = search_people(company, title)
        updated += 1

    _save_jobs(jobs, wrapper)
    print(f"✅  Saved back to jobs.json (updated recruiters for {updated} job(s))")

    
    for j in jobs[:1]:
        print("🔎 Example recruiters:", j.get("recruiters", [])[:3])


if __name__ == "__main__":
    main()
