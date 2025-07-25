from app.llm import ask_llm_stream

# --- Instructions when code execution IS allowed ---
PROMPT_INSTRUCTIONS_CAN_RUN = """
## Your Primary Goal: Decide Your Action

You must choose ONLY ONE of the following two actions.

1.  **Run the User's Code:**
    -   **Condition:** If the user's question contains command like `run`, `test`, `debug`, or `execute` their code.
    -   **Action:** Your ONLY response must be the exact text `__RUN_CODE__`. Do not add any other words or explanation.

2.  **Provide a Hint:**
    -   **Condition:** For ALL OTHER cases.
    -   **Action:** Provide a helpful hint based on the "Hinting Guidelines" below.
    -   **IMPORTANT:** NEVER respond with `__RUN_CODE__` unless the user explicitly asks for it in their question.
"""

# --- Instructions when code execution is NOT allowed ---
PROMPT_INSTRUCTIONS_CANNOT_RUN = """
## Your Primary Goal: Provide a Hint

Your ONLY goal is to provide a helpful hint to the user based on the "Hinting Guidelines" below. The user's code has already been run, and you are now providing the final feedback.

**IMPORTANT:** Do NOT run the code again. Do NOT respond with `__RUN_CODE__`.
"""

# --- Main prompt template ---
HINT_PROMPT_TEMPLATE = """
{instructions}

---

## Context for Your Decision

-   **User Question:** {user_question}
-   **Conversation History:**
    {conversation_history}
-   **Problem Title:** {problem_title}
-   **Problem Description:**
    {problem_description}
-   **User's Current Code:**
    ```python
    {user_code}
    ```
-   **Result from Last Code Run:**
    {running_result}
-   **Testcase Used:**
    {testcase}

---

## Hinting Guidelines (Only use if you decided to provide a hint)

You are an AI tutor helping a student with Python. Based on the context above, if your primary goal led you to provide a hint, follow these instructions strictly:

-   ✅ If the user's code is fully correct, clearly acknowledge it, congratulate them, and highlight what was done well.
-   ❌ If the user's code is wrong or incomplete, give a **step-by-step hint**, not a full solution. Mention the specific concept or line that needs attention.
-   🧠 Use the "Result from Last Code Run" to guide your hint. If there's an error, help the student understand its likely cause.
-   💬 Be direct, actionable, and supportive. Use Markdown for any code snippets.

### Your Output:
"""

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
    # Select the correct set of instructions based on the is_done flag
    if is_done:
        instructions = PROMPT_INSTRUCTIONS_CANNOT_RUN
    else:
        instructions = PROMPT_INSTRUCTIONS_CAN_RUN
    
    prompt = HINT_PROMPT_TEMPLATE.format(
        instructions=instructions,
        user_question=user_question,
        problem_title=problem_title,
        problem_description=problem_description,
        user_code=user_code,
        conversation_history=conversation_history,
        running_result=running_result,
        testcase=testcase
    )

    async for token in ask_llm_stream(prompt.strip()):
        print(token, end="", flush=True)
        yield token
