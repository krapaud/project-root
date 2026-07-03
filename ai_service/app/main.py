from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.runner import answer_question

app = FastAPI(title="HBntory AI Query Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    if not request.question or not request.question.strip():
        return QueryResponse(answer="Please ask a question about products or stock.")

    answer = await answer_question(request.question.strip())
    return QueryResponse(answer=answer)
