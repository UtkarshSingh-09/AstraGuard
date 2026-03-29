from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models.contracts import ApiStatus, JobCreateRequest, JobType
from app.pipelines.cams_agent import CAMSAgent
from app.pipelines.form16_agent import Form16Agent
from app.services.background_runner import background_runner
from app.services.job_registry import job_service
from app.services.secret_store import secret_store

import os
import tempfile
from fastapi import UploadFile, File, Form
from integrations.form16_extractor import extract_from_pdf
from integrations.cas_extractor import extract_from_cas
from app.engines.tax_engine import calculate_tax_comparison
from app.engines.portfolio_engine import analyze_portfolio
from app.repositories.users_repo import UsersRepository
from agents.orchestrator import run_orchestrator

router = APIRouter(prefix="/api", tags=["ingestion_agents"])
cams_agent = CAMSAgent()
form16_agent = Form16Agent()
users_repo = UsersRepository()


class CAMSAgentStartRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    pan: str = Field(..., min_length=5)
    email: str = Field(..., min_length=5)
    from_date: str | None = None
    to_date: str | None = None
    mode: str = "mock"  # set "real" to attempt playwright flow
    cams_url: str | None = None
    auto_ingest_mailbox: bool = False
    mailbox_app_password: str | None = None
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    provider_mode: str = "auto"  # auto | provider_only | playwright_only
    priority: list[str] | None = None


class Form16AgentStartRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    username: str = Field(..., min_length=2)
    password: str = Field(..., min_length=2)
    assessment_year: str | None = None
    mode: str = "assisted"  # or "mock"
    portal_url: str = "https://www.tdscpc.gov.in/"


@router.post("/cams/agent/start")
async def start_cams_agent(request: CAMSAgentStartRequest):
    payload = {
        "user_id": request.user_id,
        "mode": request.mode,
        "from_date": request.from_date,
        "to_date": request.to_date,
        "auto_ingest_mailbox": request.auto_ingest_mailbox,
        "imap_host": request.imap_host,
        "imap_port": request.imap_port,
        "provider_mode": request.provider_mode,
        "priority": request.priority or ["provider_api", "assisted_playwright", "upload_fallback"],
        "input_mask": {"pan_last4": request.pan[-4:], "email_hint": request.email[:3] + "***"},
    }
    if request.cams_url:
        payload["cams_url"] = request.cams_url

    job = job_service.create_job(
        JobCreateRequest(
            user_id=request.user_id,
            job_type=JobType.CAMS_FETCH,
            payload=payload,
        )
    )
    secrets = {"pan": request.pan, "email": request.email}
    if request.mailbox_app_password:
        secrets["mailbox_app_password"] = request.mailbox_app_password
    secret_store.put(job.job_id, secrets, ttl_seconds=900)
    background_runner.spawn(cams_agent.run(job.job_id, job.payload))
    return {
        "status": ApiStatus.PROCESSING,
        "job_id": job.job_id,
        "job_type": JobType.CAMS_FETCH,
        "message": "CAMS background agent started",
    }


@router.post("/form16/agent/start")
async def start_form16_agent(request: Form16AgentStartRequest):
    job = job_service.create_job(
        JobCreateRequest(
            user_id=request.user_id,
            job_type=JobType.FORM16_FETCH,
            payload={
                "mode": request.mode,
                "assessment_year": request.assessment_year,
                "portal_url": request.portal_url,
                "input_mask": {"username_hint": request.username[:2] + "***"},
            },
        )
    )
    secret_store.put(
        job.job_id,
        {"username": request.username, "password": request.password},
        ttl_seconds=900,
    )
    background_runner.spawn(form16_agent.run(job.job_id, job.payload))
    return {
        "status": ApiStatus.PROCESSING,
        "job_id": job.job_id,
        "job_type": JobType.FORM16_FETCH,
        "message": "Form16 background agent started",
    }


@router.post("/upload-form16")
async def upload_form16(user_id: str = Form(...), file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await extract_from_pdf(tmp_path)

        if not result.get("success"):
            return {"error": result.get("error")}

        user = await users_repo.get_user(user_id) or {}
        dna = user.get("financial_dna", {})
        new_dna = result.get("financial_dna", {})
        
        # Merge new dna into existing dna without overwriting investments
        for k, v in new_dna.items():
            if k == "existing_investments":
                if "existing_investments" not in dna:
                    dna["existing_investments"] = {}
                for inv_k, inv_v in v.items():
                    dna["existing_investments"][inv_k] = inv_v
            else:
                dna[k] = v

        await users_repo.upsert_user(
            user_id,
            {"financial_dna": dna, "form16_raw": result.get("raw_extracted"), "form16_metadata": result.get("metadata")},
        )

        tax_inputs = result.get("tax_inputs", {})
        if "base_salary" not in tax_inputs and "annual_salary" in tax_inputs:
            tax_inputs["base_salary"] = tax_inputs["annual_salary"]
            
        tax_calc = calculate_tax_comparison(tax_inputs)

        ai_result = await run_orchestrator(
            user_id=user_id,
            message="Form 16 upload hua, tax analysis karo",
            financial_dna=result.get("financial_dna"),
            calculation_result=tax_calc,
        )

        return {
            "extraction": result,
            "tax_analysis": ai_result,
        }
    finally:
        os.unlink(tmp_path)


@router.post("/upload-cas")
async def upload_cas(
    user_id: str = Form(...), 
    password: str = Form(...), 
    file: UploadFile = File(...)
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await extract_from_cas(tmp_path, password)

        if not result.get("success"):
            return {"error": result.get("error")}

        funds = result.get("funds", [])
        if not funds:
            return {"error": "No mutual funds found in this CAS statement."}

        portfolio_calc = analyze_portfolio({"funds": funds})

        user = await users_repo.get_user(user_id) or {}
        dna = user.get("financial_dna", {})
        if "existing_investments" not in dna:
            dna["existing_investments"] = {}
            
        portfolio_summary = result.get("portfolio_summary", {})
        dna["existing_investments"]["mutual_funds"] = portfolio_summary.get("total_valuation", 0.0)
        
        updates = {"financial_dna": dna}
        mobile = portfolio_summary.get("mobile")
        if mobile:
            updates["phone_number"] = mobile
            
        await users_repo.upsert_user(user_id, updates)

        ai_result = await run_orchestrator(
            user_id=user_id,
            message="Mera CAS statement upload hua hai, portfolio review karo",
            calculation_result=portfolio_calc,
        )

        return {
            "summary": result.get("portfolio_summary", {}),
            "portfolio_analysis": ai_result,
        }
    finally:
        os.unlink(tmp_path)
