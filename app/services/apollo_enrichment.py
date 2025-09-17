from __future__ import annotations
"""Apollo.io recruiter enrichment helpers (safe for import).

This is an extracted, trimmed version of logic from `apollotest.py` adapted so
it does NOT raise SystemExit on import if the API key is missing. The pipeline
can call `find_recruiter_contact` opportunistically.
"""
import os, re, requests, math, logging, time
from typing import List, Dict, Any, Optional
from app.core.config import settings

APOLLO_BASE = "https://api.apollo.io/api/v1"

RECRUITER_KEYWORDS = re.compile(
    r"\b(recruit|recruiter|talent|sourc|staffing|people\s*&?\s*culture|people ops|people partner|talent partner|human\s+resources|hrbp|hr\b|ta|acquisition)\b",
    re.IGNORECASE,
)

# Broad common recruiter titles used for an initial generic search before we try
# dynamic job-title derived phrases. This increases hit rate for companies whose
# recruiters do not include the specific role keywords in their titles.
COMMON_RECRUITER_TITLES = [
    "Recruiter","Senior Recruiter","Technical Recruiter","Sr Technical Recruiter","Sr Recruiter",
    "Talent Acquisition","Talent Acquisition Partner","Talent Acquisition Manager","Talent Partner","People Partner",
    "Director Talent Acquisition","Head of Talent","Lead Recruiter","Staffing Manager","Staffing Lead",
    "People Operations","People & Culture","HR Manager","HR Business Partner","HRBP","Sourcer","Lead Sourcer"
]

STOPWORDS = {
    "the","a","an","and","or","of","for","to","in","on","at","by","with","from",
    "ii","iii","iv","v","i","x","l","llc","inc","co","corp","company",
    "remote","hybrid","contract","full","part","time","fulltime","parttime",
    "sr","jr","senior","junior","lead","principal","staff","manager","director","head",
    "vp","chief","intern","internship","entry","mid","associate",
    "seasonal","temporary","temp","usa","united","states"
}

def _norm(s: str) -> str:
    return (s or "").strip().lower()

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-\+\.]*")

def _tokens_from_title(title: str) -> List[str]:
    tokens = [w.lower() for w in TOKEN_RE.findall(_norm(title))]
    cleaned: List[str] = []
    for w in tokens:
        w = w.strip(".+-")
        if not w or w in STOPWORDS or w.isdigit():
            continue
        cleaned.append(w)
    seen, out = set(), []
    for w in cleaned:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out

def _bigrams(words: List[str]) -> List[str]:
    out: List[str] = []
    for i in range(len(words)-1):
        bg = f"{words[i]} {words[i+1]}"
        if bg not in out:
            out.append(bg)
    return out

def _phrases(title: str) -> List[str]:
    toks = _tokens_from_title(title)
    return _bigrams(toks) + toks

def _search(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Call Apollo people search (POST JSON) and return people list.

    Previous implementation incorrectly used GET with query params which Apollo
    does not officially support for this endpoint, resulting in empty/no data.
    We now:
      * Convert *[] style keys (person_titles[]) to proper list fields.
      * Use POST JSON body per Apollo API documentation.
      * Log non-200 responses at INFO with truncated body for visibility.
      * Apply minimal retry/backoff for 429 rate-limit responses.
    """
    key = settings.APOLLO_API_KEY
    if not key:
        return []
    # Transform legacy style keys to JSON structure Apollo expects
    body: Dict[str, Any] = {}
    for k, v in params.items():
        if k.endswith("[]"):
            body[k[:-2]] = v  # strip [] -> list
        else:
            body[k] = v
    headers = {"Content-Type": "application/json", "Accept": "application/json", "X-Api-Key": key}
    attempt = 0
    while attempt < 2:  # single retry on 429
        attempt += 1
        try:
            r = requests.post(f"{APOLLO_BASE}/people/search", headers=headers, json=body, timeout=30)
        except Exception as e:  # network/runtime
            logging.info("Apollo search network_error attempt=%s err=%s company=%s", attempt, e, body.get("q_organization_name"))
            return []
        if r.status_code == 429:
            logging.info("Apollo search rate_limited retrying attempt=%s", attempt)
            time.sleep(1.2)
            continue
        if r.status_code != 200:
            snippet = r.text[:280].replace("\n", " ") if r.text else ""
            logging.info("Apollo search non_200 status=%s company=%s titles=%s body_snippet=%s", r.status_code, body.get("q_organization_name"), len(body.get("person_titles", []) or []), snippet)
            return []
        try:
            payload = r.json()
        except ValueError:
            logging.info("Apollo search invalid_json company=%s", body.get("q_organization_name"))
            return []
        data = payload.get("people") or []
        logging.debug("Apollo search returned %d people company=%s", len(data), body.get("q_organization_name"))
        return data
    return []

def _unlock_email(person_id: str) -> str:
    key = settings.APOLLO_API_KEY
    if not key or not person_id:
        return ""
    headers = {"Content-Type": "application/json", "X-Api-Key": key}
    try:
        r = requests.post(f"{APOLLO_BASE}/people/match", json={"id": person_id, "reveal_email": True}, headers=headers, timeout=25)
        if r.status_code != 200:
            logging.debug("Apollo unlock non-200 %s id=%s", r.status_code, person_id)
            return ""
        email = r.json().get("person", {}).get("email") or ""
        if not email:
            logging.debug("Apollo unlock empty email id=%s", person_id)
        return email
    except Exception as e:
        logging.debug("Apollo unlock exception %s id=%s", e, person_id)
        return ""

def _title_is_recruiting(title: str, phrases: List[str]) -> bool:
    t = _norm(title)
    if not t or not RECRUITER_KEYWORDS.search(t):
        return False
    for p in phrases:
        pp = _norm(p)
        if pp and pp in t:
            return True
    return any(k in t for k in ("recruiter", "talent acquisition", "sourc", "hiring manager"))

def _filter_rank(people: List[Dict[str, Any]], phrases: List[str]) -> List[Dict[str, str]]:
    SENIORITY_SCORES = {"principal":6,"director":6,"head":6,"vp":6,"lead":5,"senior":4,"manager":4,"partner":4,"specialist":3,"coordinator":2,"recruiter":5,"sourcer":4,"hr":3}
    cleaned: List[Dict[str,str]] = []
    for p in people:
        title = p.get("title") or p.get("person_title") or ""
        if not _title_is_recruiting(title, phrases):
            continue
        name = (f"{p.get('first_name','')} {p.get('last_name','')}".strip() or p.get("name",""))
        cleaned.append({"name": name, "title": title, "id": p.get("id",""), "linkedin_url": p.get("linkedin_url") or p.get("person_linkedin_url") or ""})

    def score(t: str) -> int:
        t = _norm(t)
        sc = 0
        if RECRUITER_KEYWORDS.search(t): sc += 5
        for k,v in SENIORITY_SCORES.items():
            if k in t: sc += v
        for ph in phrases:
            ph = _norm(ph)
            if ph and ph in t: sc += 3
        if "talent acquisition" in t: sc += 3
        if "recruit" in t: sc += 3
        if "sourc" in t: sc += 2
        return sc
    cleaned.sort(key=lambda x: score(x["title"]), reverse=True)
    return cleaned

_CONTACT_CACHE: dict[tuple[str,str], dict] = {}

def find_recruiter_contact(company: str, job_title: str) -> Optional[Dict[str,str]]:
    """Return best recruiter contact dict or None.

    Strategy:
      1. Generic recruiter titles search (COMMON_RECRUITER_TITLES) for the company.
      2. Dynamic titles derived from the job title (phrases + recruiter variants).
      3. Broad company people search filtered for recruiting keywords.
    The first successful ranked result triggers an email unlock attempt.
    """
    if not company or not job_title or not settings.APOLLO_API_KEY:
        return None
    phrases = _phrases(job_title)
    cache_key = (_norm(company), _norm(job_title))
    if cache_key in _CONTACT_CACHE:
        logging.info("Apollo cache hit company=%s title=%s", company, job_title)
        return _CONTACT_CACHE[cache_key]

    # 1. Generic recruiter search
    params_generic = {
        "q_organization_name": company,
        "page": 1,
        "per_page": 60,
        "person_locations[]": "United States",
        "person_titles[]": COMMON_RECRUITER_TITLES,
    }
    logging.info("Apollo phase=generic company=%s title=%s", company, job_title)
    people_generic = _search(params_generic)
    ranked = _filter_rank(people_generic, phrases)

    # 2. Dynamic titles if generic failed or produced weak/no results
    if not ranked:
        dynamic_titles: list[str] = []
        for ph in phrases[:15]:
            dynamic_titles.extend([
                f"{ph} recruiter", f"{ph} sourcer", f"{ph} talent acquisition",
                f"recruiter {ph}", f"talent {ph}", f"{ph} staffing"
            ])
        if dynamic_titles:
            params_dynamic = {
                "q_organization_name": company,
                "page": 1,
                "per_page": 60,
                "person_locations[]": "United States",
                "person_titles[]": dynamic_titles[:80],
            }
            logging.info("Apollo phase=dynamic company=%s title=%s titles=%d", company, job_title, len(dynamic_titles))
            people_dyn = _search(params_dynamic)
            ranked = _filter_rank(people_dyn, phrases)

    # 3. Broad fallback
    if not ranked:
        logging.info("Apollo phase=broad company=%s title=%s", company, job_title)
        people_broad = _search({
            "q_organization_name": company,
            "page": 1,
            "per_page": 60,
            "person_locations[]": "United States"
        })
        ranked = _filter_rank(people_broad, phrases)

    # 4. Location-relaxed fallback (no person_locations[] constraint) if still empty
    if not ranked:
        logging.info("Apollo phase=relaxed company=%s title=%s", company, job_title)
        relaxed = _search({
            "q_organization_name": company,
            "page": 1,
            "per_page": 60,
        })
        ranked = _filter_rank(relaxed, phrases)

    if not ranked:
        logging.info("Apollo enrichment: none_found company=%s title=%s", company, job_title)
        return None
    top = ranked[0]
    email = _unlock_email(top.get("id", "")) or ""
    if not email:
        logging.info("Apollo enrichment: email_locked company=%s title=%s recruiter=%s", company, job_title, top)
    result = {
        "name": top["name"],
        "title": top["title"],
        "email": email,
        "linkedin_url": top.get("linkedin_url", "")
    }
    _CONTACT_CACHE[cache_key] = result
    return result

def search_recruiter_contacts(company: str, job_title: str, max_results: int = 5):
    """Return list of recruiter contacts (name,title,email,linkedin_url) with real unlocked emails only.

    This adapts broader logic from apollotest.py while stripping any placeholder
    or synthetic fallback addresses. Only contacts for which an email is
    successfully unlocked are returned. Order reflects ranking by title
    relevance & seniority.
    """
    if not company or not job_title or not settings.APOLLO_API_KEY:
        return []
    phrases = _phrases(job_title)
    # Phase 1: generic recruiter titles
    generic_params = {
        "q_organization_name": company,
        "person_titles[]": COMMON_RECRUITER_TITLES,
        "page": 1,
        "per_page": 100,
        "person_locations[]": "United States",
    }
    people_generic = _search(generic_params)
    ranked = _filter_rank(people_generic, phrases)

    # Phase 2: dynamic titles if needed
    if not ranked:
        dyn_titles = []
        for ph in _phrases(job_title)[:20]:
            dyn_titles.extend([
                f"{ph} recruiter", f"{ph} sourcer", f"{ph} talent acquisition", f"{ph} hiring manager"
            ])
        params_dyn = {
            "q_organization_name": company,
            "person_titles[]": dyn_titles[:100],
            "page": 1,
            "per_page": 100,
            "person_locations[]": "United States",
        }
        ranked = _filter_rank(_search(params_dyn), phrases)

    # Phase 3: broad fallback (still no synthetic email)
    if not ranked:
        broad = _search({
            "q_organization_name": company,
            "page": 1,
            "per_page": 100,
            "person_locations[]": "United States",
        })
        ranked = _filter_rank(broad, phrases)

    contacts = []
    for p in ranked:
        if len(contacts) >= max_results:
            break
        email = _unlock_email(p.get("id", "")) or ""
        if not email:
            continue  # skip entries without real unlocked email
        contacts.append({
            "name": p.get("name"),
            "title": p.get("title"),
            "email": email,
            "linkedin_url": p.get("linkedin_url"),
        })
    return contacts

__all__ = ["find_recruiter_contact", "search_recruiter_contacts"]