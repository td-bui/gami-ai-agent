from app.llm import ask_llm_stream

# --- Instructions when code execution IS allowed ---
PROMPT_INSTRUCTIONS_CAN_RUN = """
## Your Task: Follow these steps precisely.

**Step 1: Analyze the User's Intent**
- Read the "User Question" in the context below.
- Does the question contain a direct command to `run`, `test`, `execute`, or `debug` the code?

**Step 2: Make Your Decision**
- IF the answer to Step 1 is YES, your decision is to "Run the Code".
- IF the answer to Step 1 is NO, your decision is to "Provide a Hint".

**Step 3: Generate Your Final Output**
- If your decision was "Run the Code", your entire output MUST be the single, exact phrase: `__RUN_CODE__`
- If your decision was "Provide a Hint", use the "Hinting Guidelines" to write a helpful hint.

**IMPORTANT:** Do not output the steps themselves. Your final response must be ONLY the result from Step 3.
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
    # --- Start of added debugging code ---
    print("\n--- HINT AGENT INPUTS ---")
    print(f"User Question: '{user_question}'")
    print(f"Problem Title: '{problem_title}'")
    print(f"User Code:\n{user_code}")
    print(f"Conversation History:\n{conversation_history}")
    print(f"Running Result: '{running_result}'")
    print(f"Testcase: '{testcase}'")
    print(f"Is Done: {is_done}")
    print("--------------------------\n")
    # --- End of added debugging code ---

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
