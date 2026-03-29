from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.pipelines.document_monitor import DocumentMonitor

router = APIRouter(prefix="/api/documents", tags=["documents"])
monitor = DocumentMonitor()


class ValidateDocumentRequest(BaseModel):
    file_path: str = Field(..., min_length=3)
    expected_type: str = Field(default="any")
    extracted_text: str = Field(default="")


@router.post("/validate")
async def validate_document(request: ValidateDocumentRequest):
    result = monitor.validate(
        request.file_path,
        expected_type=request.expected_type,  # type: ignore[arg-type]
        extracted_text=request.extracted_text,
    )
    return {
        "status": "success" if result.accepted else "error",
        "accepted": result.accepted,
        "document_type": result.document_type,
        "confidence": round(result.confidence, 2),
        "reason": result.reason,
    }
