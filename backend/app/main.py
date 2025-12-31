from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import os
import json
from .models import RecommendationResponse, MatchResult, Job, Resume
from .matching.matcher import Matcher
from .resume_parser import ResumeParser
from .email_client import EmailClient
from .config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Recruiting Agent",
    description="AI-powered candidate matching system",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
matcher = Matcher()
resume_parser = ResumeParser()
email_client = EmailClient()


def load_jobs() -> List[Job]:
    """Load jobs from data/jobs directory"""
    jobs = []
    jobs_dir = settings.jobs_dir

    if not os.path.exists(jobs_dir):
        logger.warning(f"Jobs directory not found: {jobs_dir}")
        return jobs

    for filename in os.listdir(jobs_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(jobs_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)
                    jobs.append(Job(**job_data))
            except Exception as e:
                logger.error(f"Error loading job {filename}: {e}")

    return jobs


def load_resumes() -> List[Resume]:
    """Load and parse all resumes from data/resumes directory"""
    resumes = []
    resumes_dir = settings.resumes_dir

    if not os.path.exists(resumes_dir):
        logger.warning(f"Resumes directory not found: {resumes_dir}")
        os.makedirs(resumes_dir, exist_ok=True)
        return resumes

    for filename in os.listdir(resumes_dir):
        filepath = os.path.join(resumes_dir, filename)

        # Skip directories
        if os.path.isdir(filepath):
            continue

        try:
            # Parse resume
            parsed_data = resume_parser.parse_file(filepath)

            # Создаем Resume объект со всеми полями
            resume = Resume(
                id=filename,
                raw_text=parsed_data['raw_text'],
                # Основная информация
                name=parsed_data.get('name'),
                email=parsed_data.get('email'),
                phone=parsed_data.get('phone'),
                location=parsed_data.get('location'),
                # Профессиональная информация
                summary=parsed_data.get('summary'),
                skills=parsed_data.get('skills', []),
                years_of_experience=parsed_data.get('years_of_experience'),
                # Опыт работы
                work_experience=parsed_data.get('work_experience', []),
                experience=parsed_data.get('experience', ''),  # Для обратной совместимости
                # Образование
                education_details=parsed_data.get('education_details', []),
                education=parsed_data.get('education', ''),  # Для обратной совместимости
                # Дополнительная информация
                languages=parsed_data.get('languages', []),
                certifications=parsed_data.get('certifications', []),
                projects=parsed_data.get('projects', [])
            )
            resumes.append(resume)
            logger.info(f"Loaded resume: {filename}")
        except Exception as e:
            logger.error(f"Error parsing resume {filename}: {e}")

    return resumes


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Recruiting Agent API",
        "version": "1.0.0",
        "endpoints": {
            "recommendations": "/recommendations?job_id={job_id}&method={method}",
            "jobs": "/jobs",
            "resumes": "/resumes",
            "fetch_resumes": "/fetch-resumes"
        }
    }


@app.get("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    job_id: Optional[str] = Query(None, description="Job ID"),
    job_text: Optional[str] = Query(None, description="Job description text"),
    method: str = Query("hybrid", description="Matching method: only 'hybrid' supported (two-layer architecture)"),
    top_k: int = Query(3, description="Number of top candidates to return (default: 3)")
):
    """
    Get candidate recommendations using two-layer architecture

    New Architecture (v2.0):
    - Layer 1: Dual vector search with Qwen embeddings (skills + experience) → Top-5
      * Skills weighted 60%, Experience weighted 40%
    - Layer 2: Mistral LLM re-ranking with detailed reasoning → Top-3

    This approach provides:
    - Accurate matching via specialized embeddings for skills and experience
    - Deep candidate analysis via LLM evaluation
    - Detailed explanations for each ranking to support hiring decisions

    BREAKING CHANGE: Only 'hybrid' method is supported in v2.0.
    Legacy methods ('embedding', 'llm') have been removed.

    Supports both Russian and English resumes and job descriptions.
    """
    # Validate method
    if method != "hybrid":
        raise HTTPException(
            status_code=400,
            detail="Only 'hybrid' method is supported. Legacy methods (embedding, llm) have been removed in v2.0."
        )

    # Get job description
    job_description = None
    job_title = "Custom Job"

    if job_id:
        # Load from jobs directory
        jobs = load_jobs()
        job = next((j for j in jobs if j.id == job_id), None)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        job_description = f"{job.title}\n\n{job.description}\n\nRequirements:\n{job.requirements}"
        if job.tech_stack:
            job_description += f"\n\nTech Stack: {', '.join(job.tech_stack)}"
        job_title = job.title

    elif job_text:
        job_description = job_text
    else:
        raise HTTPException(status_code=400, detail="Either job_id or job_text must be provided")

    # Load resumes
    resumes = load_resumes()

    if not resumes:
        raise HTTPException(status_code=404, detail="No resumes found")

    # Get recommendations
    try:
        results = matcher.get_recommendations(
            job_description=job_description,
            resumes=[r.model_dump() for r in resumes],
            method=method,
            top_k=top_k
        )

        candidates = [MatchResult(**r) for r in results]

        return RecommendationResponse(
            job_id=job_id or "custom",
            job_title=job_title,
            candidates=candidates,
            method=method
        )
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs")
async def list_jobs():
    """List all available jobs"""
    jobs = load_jobs()
    return {"jobs": jobs, "count": len(jobs)}


@app.post("/jobs")
async def create_job(job: Job):
    """Create a new job posting"""
    jobs_dir = settings.jobs_dir

    # Create jobs directory if it doesn't exist
    if not os.path.exists(jobs_dir):
        os.makedirs(jobs_dir, exist_ok=True)

    # Generate filename from job id
    filename = f"{job.id}.json"
    filepath = os.path.join(jobs_dir, filename)

    # Check if job already exists
    if os.path.exists(filepath):
        raise HTTPException(status_code=400, detail=f"Job with ID {job.id} already exists")

    # Save job to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(job.model_dump(), f, indent=2, ensure_ascii=False)

        logger.info(f"Created new job: {job.id}")
        return {"message": "Job created successfully", "job": job}
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resumes")
async def list_resumes():
    """List all available resumes with full details"""
    resumes = load_resumes()
    return {"resumes": [r.model_dump() for r in resumes], "count": len(resumes)}


@app.post("/fetch-resumes")
async def fetch_resumes_from_email(
    max_emails: int = Query(5, description="Maximum number of emails to process")
):
    """
    Fetch new resumes from email

    Only processes the most recent emails to avoid timeout.
    Looks for attachments with extensions: .pdf, .doc, .docx, .txt, .png, .jpg, .jpeg
    """
    try:
        saved_files = email_client.fetch_resumes(unread_only=True, max_emails=max_emails)
        return {
            "message": f"Fetched {len(saved_files)} new resumes",
            "files": saved_files
        }
    except Exception as e:
        logger.error(f"Error fetching resumes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
