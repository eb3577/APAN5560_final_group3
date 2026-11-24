"""OWNER: Erik. Run with: uvicorn main:app --reload --port 8000."""
from fastapi import FastAPI, HTTPException
from app.health_assistant import explain
from helper_lib.errors import ComponentNotImplemented, ResourceUnavailable, InvalidGeneratedAnswer
from helper_lib.schemas import ExplainRequest, ExplainResponse

app = FastAPI(
    title="Personalized Health Education Assistant",
    description="Health education with sources and adjustable explanation levels.",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "stage": "integration", "pipeline_ready": False,
            "note": "Server is running; model quality is still under review."}


@app.post("/explain", response_model=ExplainResponse,
          responses={501: {"description": "Component not implemented"},
                     503: {"description": "Required resource unavailable"},
                     502: {"description": "Generated answer has invalid citations"},
                     422: {"description": "Invalid request"}})
def explain_health(request: ExplainRequest):
    try:
        return explain(request)
    except ComponentNotImplemented as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ResourceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    except InvalidGeneratedAnswer as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Request could not be processed; "
                            "try a shorter question. If it persists, check server data validation.") from exc
