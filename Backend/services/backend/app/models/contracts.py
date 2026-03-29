from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobType(str, Enum):
    CAMS_FETCH = "cams_fetch"
    FORM16_FETCH = "form16_fetch"
    DOCUMENT_PARSE = "document_parse"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_USER_STEP = "awaiting_user_step"
    DOWNLOADED = "downloaded"
    PARSED = "parsed"
    COMPLETE = "complete"
    FAILED = "failed"


class ApiStatus(str, Enum):
    SUCCESS = "success"
    PROCESSING = "processing"
    ERROR = "error"


class UserStepType(str, Enum):
    OTP = "otp"
    CAPTCHA = "captcha"
    MFA_CODE = "mfa_code"


class JobCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    job_type: JobType
    payload: dict[str, Any] = Field(default_factory=dict)


class JobCreateResponse(BaseModel):
    status: ApiStatus
    job_id: str
    job_type: JobType
    job_status: JobStatus
    message: str


class JobUserStepRequest(BaseModel):
    step_type: UserStepType
    value: str = Field(..., min_length=1)


class JobState(BaseModel):
    job_id: str
    user_id: str
    job_type: JobType
    status: JobStatus
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
