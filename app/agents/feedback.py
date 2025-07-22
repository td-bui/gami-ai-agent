from app.llm import ask_llm_stream

async def code_feedback(problem_title: str, problem_description: str, user_code: str, running_result: str = ""):
    prompt = f"""
You are CodeXP, an expert Python tutor for beginner and intermediate programmers.

Review the code below and provide clear, direct feedback.

---

Problem Title: {problem_title}

Problem Description:
{problem_description}

User Code:
{user_code}

{"Code Running Result:\n" + running_result if running_result else ""}

---

Instructions:
- If the code is correct, simply say: "**Correct.**" followed by **one short sentence** to reinforce what the user did right.
- If there are mistakes, point them out **clearly and directly**, and suggest the **most important fix first**.
- Prefer **concise, high-impact suggestions** over long explanations or lists.
- If you have an improvement or cleaner solution, briefly show it using a Markdown code block.
- Do **not** overpraise or say "good job" unless it's earned through a specific insight.
- Avoid filler words. Focus on what's correct, what's wrong, and what's better.
- Only use plain text and Markdown. No HTML. No placeholder text.
- Avoid repeating the problem description or user code.

---

Now give **clear, concise, and actionable feedback**:

"""
    feedback = ""
    async for token in ask_llm_stream(prompt.strip()):
        feedback += token
    yield feedback