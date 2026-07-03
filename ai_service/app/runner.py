from google.adk.runners import InMemoryRunner
from google.genai import types

from app.inventory_agent import build_agent

APP_NAME = "hbntory_ai_query_service"


async def answer_question(question: str) -> str:
    agent = build_agent()
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    user_id = "anonymous"

    session = await runner.session_service.create_session(app_name=APP_NAME, user_id=user_id)
    content = types.Content(role="user", parts=[types.Part(text=question)])

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts if p.text)

    return final_text or "I could not generate a response for that question."
