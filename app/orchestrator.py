from langchain.chains.router import MultiPromptChain
from langchain.prompts import PromptTemplate
from app.agents.explain import explain_lesson
from app.agents.hint import generate_hint
from app.agents.feedback import code_feedback
from app.agents.conversation import generate_conversational_response
from app.agents.suggest_problem import suggest_next
from app.db import save_ai_assistance  # Make sure to implement create_new_session
from app.llm import ask_llm_stream  # Ensure this is implemented to stream LLM responses
from app.db import fetch_previous_conversations
import httpx
import asyncio
import json
import os
from app.db import get_solution_code, get_testcases  # Make sure to implement get_testcases

EXEC_API_BASE = os.getenv("EXEC_API_BASE", "http://localhost:8001")  # Change to your exec service base URL

ROUTER_PROMPT = """
You are an AI orchestrator. Decide which agent to use based on the user's request, the recent conversation, and the last agent used.

Available Agents:
1. suggest_problem
    Use when the user:
    - Asks for a new or related lesson or problem to try
    - Requests a challenge, recommended task, or next thing to learn
    - Says phrases like:
        - "Give me a related lesson"
        - "What's next?"
        - "I want to practice more"
        - "Show me another problem"
        - "What should I do now?"
        - "Continue"

    ✅ Use when the user wants to move forward or get something new to work on
    ❌ Do NOT use if the user is stuck on a current problem and needs help with it
2. explain
    Use when the user:
    - Asks for a general explanation, concept, syntax, or how something works in Python
    - Wants to understand a topic or lesson but does NOT want a new activity or problem to try

    ✅ Use if the user is learning or asking about a concept without providing code or requesting new tasks
    ❌ Do NOT use if the user:
        - Provides code or asks for help testing or fixing it
        - Asks for a new or related lesson/problem, challenge, or what to do next

3. hint
    Use when the user:
    - Shares code and asks for help (e.g. fix, improve, debug, test)
    - Asks for a hint, step-by-step help, or how to write/change code

    ✅ Use for interactive help with current code or solving a current problem
    ❌ Do NOT use if the user only wants to learn a concept or move to a new activity

4. conversation
    Use for any other case that does not fit the agents above.
    - Greetings (e.g. "hi", "hello")
    - Closings or affirmations (e.g. "ok", "thanks", "got it")
    - General chit-chat or questions about the AI itself.

    ✅ Use as a default for any input that is not a clear request for explanation, a hint, or a new problem.


Last agent: {last_agent}
Recent conversation:
{conversation_history}

User input: {user_input}

Reply with ONLY the agent name: explain, hint, suggest_problem, or conversation. Do NOT explain or answer the user's question.
Agent:
"""



async def route_to_agent_stream(user_input: str, extra: dict = None):
    print(f"Routing user extra: {extra}", flush=True)
    agent_kwargs = {
            "session_id": extra.get("session_id") if extra else None,
            "user_question": user_input,
            "topic": extra.get("topic") if extra else None,
            "lesson_id": int(extra.get("lesson_id")) if extra and extra.get("lesson_id")  else None,
            "user_id": int(extra.get("user_id")) if extra and extra.get("user_id") else None,
            "problem_id": int(extra.get("problem_id")) if extra and extra.get("problem_id") else None,
            "problem_title": extra.get("problem_title") if extra else "",
            "problem_description": extra.get("problem_description") if extra else "",
            "user_code": extra.get("user_code") if extra else "",
            "solved_problems": extra.get("solved_problems") if extra else [],
            "available_problems": extra.get("available_problems") if extra else [],
            "user_level": extra.get("user_level") if extra else "beginner",
            "user_stats": extra.get("user_stats") if extra else {},
            "last_agent": extra.get("last_agent", "explain") if extra else "explain",
            "running_result": extra.get("running_result", "") if extra else "",
            "testcase": extra.get("testcase", "") if extra else ""
        }
    try:
        # --- This block is changed to use OpenAI instead of Ollama ---
        router_prompt_text = ROUTER_PROMPT.format(
            user_input=user_input,
            conversation_history="", # We will add this later
            last_agent=agent_kwargs["last_agent"]
        )

        previous_context = ""
        prev_convos = await fetch_previous_conversations(agent_kwargs["lesson_id"],
                                                          agent_kwargs["problem_id"],
                                                          agent_kwargs["session_id"],
                                                          agent_kwargs["user_id"])
        if prev_convos:
            # If too many previous conversations, summarize them
            MAX_CONTEXT_CHARS = 4000  # or any limit you want
            for convo in prev_convos:
                previous_context += f"User: {convo['user_query']}\nAI: {convo['ai_response']}\n"
            if len(previous_context) > MAX_CONTEXT_CHARS:
                # Summarize the previous context using the LLM itself
                summary_prompt = f"Summarize the following conversation history for context in 5 concise bullet points:\n{previous_context}"
                summary = ""
                # Use ask_llm_stream to get the summary
                async for token in ask_llm_stream(summary_prompt.strip()):
                    summary += token
                previous_context = "\nSummary of previous conversation history:\n" + summary.strip() + "\n"
        
        conversation_history = previous_context.strip()

        # Update the router prompt with the conversation history
        router_prompt_with_history = ROUTER_PROMPT.format(
            user_input=user_input,
            conversation_history=conversation_history,
            last_agent=agent_kwargs["last_agent"]
        )

        # Get the agent decision from OpenAI
        agent = ""
        async for token in ask_llm_stream(router_prompt_with_history):
            agent += token
        agent = agent.strip().lower()

        found = False
        ai_response = ""  # Collect the response here

        async def stream_and_collect(generator):
            nonlocal found, ai_response
            async for token in generator:
                found = True
                ai_response += token
                yield token

        # Get session_id from extra if present
        session_id = extra.get("session_id") if extra else None
        print (f"Routing to agent: {agent}", flush=True)

        # Pass conversation_history to all agents
        if agent == "explain":
            generator = explain_lesson(
                user_question=agent_kwargs["user_question"],
                topic=agent_kwargs["topic"],
                conversation_history=conversation_history
            )
        elif agent == "hint":
            generator = generate_hint(
                agent_kwargs["user_question"],
                agent_kwargs["problem_title"],
                agent_kwargs["problem_description"],
                agent_kwargs["user_code"],
                conversation_history=conversation_history,
                running_result=agent_kwargs["running_result"],
                testcase=agent_kwargs["testcase"],
                is_done=False  # Indicate this is an initial hint before running code
            )
            response = ""
            async for token in generator:
                found = True
                ai_response += token
                response += token
                yield token

            # TOOL USE: If LLM requests code execution
            if response.strip() == "__RUN_CODE__":
                print("Running code execution...", flush=True)
                code_result = await execute_code(
                    agent_kwargs["user_code"],
                    agent_kwargs.get("problem_id")
                )
                yield "__RUN_CODE_DONE__"
                # Now call generate_hint again, but YIELD its tokens!
                generator = generate_hint(
                    agent_kwargs["user_question"],
                    agent_kwargs["problem_title"],
                    agent_kwargs["problem_description"],
                    agent_kwargs["user_code"],
                    conversation_history=conversation_history,
                    running_result=code_result,
                    testcase=agent_kwargs["testcase"],
                    is_done=True  # Indicate this is the final hint after running code
                )
                async for token in generator:
                    found = True
                    ai_response += token
                    yield token
        elif agent == "suggest_problem":
            # Pass extra context to suggest_next
            generator = suggest_next(
                agent_kwargs["user_id"],
                user_input,
                agent_kwargs["user_level"],
                {
                    "lessonId": agent_kwargs["lesson_id"],
                    "problemId": agent_kwargs["problem_id"],
                    "topic": agent_kwargs["topic"]
                }
            )
        elif agent == "conversation":
            generator = generate_conversational_response(
                user_input=user_input,
                conversation_history=conversation_history
            )
        else:
            generator = None

        if generator:
            async for token in stream_and_collect(generator):
                yield token

        if not found:
            yield "Sorry, no response was generated."

        # Save to DB after streaming is done
        if found:
            lesson_id = agent_kwargs["lesson_id"]
            problem_id = extra.get("problem_id") if extra else None
            user_id = agent_kwargs["user_id"]

            # Save the AI assistance with session_id
            await save_ai_assistance(
                user_id=user_id,
                lesson_id=lesson_id,
                problem_id=problem_id,
                session_id=session_id,
                user_query=user_input,
                ai_response=ai_response,
                suggestion_type=agent
            )

    except Exception as e:
        yield f"Error: {str(e)}"



async def execute_code(user_code: str, problem_id=None):
    # If problem_id is provided, use /execute-problem and /result-problem
    if problem_id:
        solution_code = await get_solution_code(problem_id) or ""
        # Prepare test cases
        testcases = await get_testcases(problem_id)
        payload = {
            "userCode": user_code,
            "solutionCode": solution_code,
            "testCases": testcases
        }
        print(f"Payload for /execute-problem: {json.dumps(payload, ensure_ascii=False)}", flush=True) 
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{EXEC_API_BASE}/execute-problem", json=payload)
            resp.raise_for_status()
            job_id = resp.json().get("job_id")
            # Poll for result
            for _ in range(30):
                result_resp = await client.get(f"{EXEC_API_BASE}/result-problem/{job_id}")
                result = result_resp.json()
                if result["status"] == "finished":
                    return json.dumps(result["results"], ensure_ascii=False)
                elif result["status"] == "failed":
                    return f"Error: {result.get('error', 'Job failed')}"
                await asyncio.sleep(0.5)
            return "Error: Code execution timed out."
    # If no problem_id, use /execute and /result
    else:
        payload = {"code": user_code}
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{EXEC_API_BASE}/execute", json=payload)
            resp.raise_for_status()
            job_id = resp.json().get("job_id")
            # Poll for result
            for _ in range(30):
                result_resp = await client.get(f"{EXEC_API_BASE}/result/{job_id}")
                result = result_resp.json()
                if result["status"] == "finished":
                    return result.get("output", "")
                elif result["status"] == "failed":
                    return f"Error: {result.get('error', 'Job failed')}"
                await asyncio.sleep(0.5)
            return "Error: Code execution timed out."