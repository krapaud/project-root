import os

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.auth import NotAuthenticatedError
from app.database import Base, engine
from app.routes import auth_routes, stock_routes, user_routes

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HBntory Backoffice")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "dev-secret-change-me"),
)


@app.exception_handler(NotAuthenticatedError)
async def redirect_to_login(request: Request, exc: NotAuthenticatedError) -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)


app.include_router(auth_routes.router)
app.include_router(stock_routes.router)
app.include_router(user_routes.router)
