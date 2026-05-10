from fastapi import APIRouter, Depends, HTTPException, status

from app import models, schemas
from app.ai_summary import SummarizationConfigError, SummarizationError, generate_summary
from app.dependencies import get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/summarize", response_model=schemas.SummaryResponse)
def summarize_text(
    request: schemas.SummaryRequest,
    _: models.User = Depends(get_current_user),
):
    try:
        summary = generate_summary(request.text)
    except SummarizationConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except SummarizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return schemas.SummaryResponse(summary=summary)
