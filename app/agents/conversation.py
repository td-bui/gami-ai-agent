from app.llm import ask_llm_stream

CONVERSATION_PROMPT = """You are a friendly and helpful AI Python tutor name CodePlay AI. The user has said something that doesn't require a specific tool or explanation. Respond conversationally and briefly.

Recent conversation:
{conversation_history}

User input: {user_input}

Your response:
"""

async def generate_conversational_response(user_input: str, conversation_history: str):
    """Generates a simple conversational response."""
    prompt = CONVERSATION_PROMPT.format(
        user_input=user_input,
        conversation_history=conversation_history
    )
    async for token in ask_llm_stream(prompt):
        yield token