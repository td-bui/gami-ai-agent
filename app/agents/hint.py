from app.llm import ask_llm_stream

async def generate_hint(
    user_question: str = "",
    problem_title: str = "",
    problem_description: str = "",
    user_code: str = "",
    conversation_history: str = "",
    running_result: str = "",
    testcase: str = "",
    is_done: bool = False
):
    prompt_parts = []
    
    if not is_done:
        prompt_parts.append(
            "IMPORTANT: If the user's question contains command like 'run', 'test', 'debug', or 'execute', respond ONLY with: __RUN_CODE__ (do not reply with anything else)."
        )
        prompt_parts.append("")

    # Context building
    if user_question:
        prompt_parts.append(f"User Question: {user_question}")
    if conversation_history:
        prompt_parts.append(f"Conversation history:\n{conversation_history}")
    if problem_title:
        prompt_parts.append(f"Problem Title: {problem_title}")
    if problem_description:
        prompt_parts.append(f"Problem Description:\n{problem_description}")
    if user_code:
        prompt_parts.append(f"User Code:\n{user_code}")
    if running_result:
        prompt_parts.append(f"Code Running Result:\n{running_result}")
    if testcase:
        prompt_parts.append(f"Testcase:\n{testcase}")

    # Improved instructions
    prompt_parts.append(
        """
## Your Task:

You are an AI tutor helping a student with Python programming. Based on the provided context, follow these instructions strictly:

- ✅ If the user's code is fully correct:
  - **Clearly acknowledge** that the code is correct.
  - Congratulate the student briefly and **highlight what was done well**.
  - Do NOT over-explain or introduce unrelated concepts.

- ❌ If the user's code is wrong or incomplete:
  - Give a **step-by-step hint**, not a full solution.
  - Mention the **specific concept, keyword, or line** that likely needs attention.
  - Be **direct, actionable, and supportive**.
  - You may include a **short code snippet** (one line or so) to clarify the hint.

- 🧠 Use running result or testcase info to guide your hint. If there's an error or failure, help the student **understand the likely cause**.

- 💬 Always speak clearly in plain English.
  - Do NOT use HTML or placeholder tags.
  - Use **Markdown** formatting for any code: wrap code blocks in triple backticks (```python).

### Your Output:

Now, write the most helpful and concise hint or feedback for the student below:
"""
    )

    prompt = "\n".join(prompt_parts)

    async for token in ask_llm_stream(prompt.strip()):
        print(token, end="", flush=True)
        yield token
