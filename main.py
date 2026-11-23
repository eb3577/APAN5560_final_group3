"""OWNER: Erik. Run with: uvicorn main:app --reload --port 8000."""
from fastapi import FastAPI, HTTPException
from app.health_assistant import explain
from helper_lib.errors import ComponentNotImplemented, ResourceUnavailable
from helper_lib.schemas import ExplainRequest, ExplainResponse

app = FastAPI(
    title="Personalized Health Education Assistant",
    description="Health education with sources and adjustable explanation levels.",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "stage": "scaffold", "pipeline_ready": False}


@app.post("/explain", response_model=ExplainResponse,
          responses={501: {"description": "Component not implemented"},
                     503: {"description": "Required resource unavailable"}})
def explain_health(request: ExplainRequest):
    try:
        return explain(request)
    except ComponentNotImplemented as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ResourceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

# TODO Erik: check actual pipeline readiness after integration.
