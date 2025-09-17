from __future__ import annotations
"""Helpers to materialize resume_custom fields to disk and build a zip archive.

Public functions:
 - ensure_resume_files(run, jobs) -> list[str]: writes each job.resume_custom to generated_docs/run_<id>/resume_job<job_id>.txt and .docx
 - create_resume_zip(run) -> path to created zip file (rebuilds from current txt/docx files)

We intentionally keep logic lightweight (no heavy docx templating). A simple text->docx conversion
reuses the existing coverletter_convertion.convert_cover_letter helper for consistency.
"""
from pathlib import Path
from typing import Iterable, List
import zipfile
import os

from app.models import PipelineRun, ScrapedJob
from coverletter_convertion import convert_cover_letter

PROJECT_ROOT = Path(os.getcwd()).resolve()

def _run_output_dir(run_id: int) -> Path:
    return PROJECT_ROOT / 'generated_docs' / f'run_{run_id}'

def ensure_resume_files(run: PipelineRun, jobs: Iterable[ScrapedJob]) -> List[str]:
    out_dir = _run_output_dir(run.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    for j in jobs:
        if not j.resume_custom:
            continue
        txt_path = out_dir / f"resume_job{j.id}.txt"
        docx_path = out_dir / f"resume_job{j.id}.docx"
        try:
            # Always (re)write text file (idempotent, small)
            txt_path.write_text(j.resume_custom, encoding='utf-8')
            # Convert to docx (best effort)
            try:
                convert_cover_letter(str(txt_path), str(docx_path))
            except Exception:
                pass
            written.append(str(txt_path))
            written.append(str(docx_path))
        except Exception:
            continue
    return written

def create_resume_zip(run: PipelineRun) -> str:
    out_dir = _run_output_dir(run.id)
    if not out_dir.exists():
        raise FileNotFoundError("No generated docs directory for run")
    zip_path = out_dir / f"run_{run.id}_resumes.zip"
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out_dir.glob('resume_job*.*')):
            try:
                zf.write(p, arcname=p.name)
            except Exception:
                continue
    return str(zip_path)

__all__ = [
    'ensure_resume_files',
    'create_resume_zip',
]
