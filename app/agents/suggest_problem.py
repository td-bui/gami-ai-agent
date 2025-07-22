import pinecone
import openai
import asyncpg
import json
import asyncio
import re
import os

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "gami-ai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

PG_CONN = {
    "database": os.getenv("PGDATABASE", "gami-ai"),
    "user": os.getenv("PGUSER", "thangbui"),
    "password": os.getenv("PGPASSWORD", "password"),
    "host": os.getenv("PGHOST", "localhost"),
    "port": os.getenv("PGPORT", "5432")
}

# Initialize Pinecone
pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

def get_embedding(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

async def fetch_user_history(user_id):
    """
    Returns a set of completed problem and lesson IDs for the given user.
    """
    conn = await asyncpg.connect(**PG_CONN)
    # Fetch solved problems (status = 'Accepted')
    solved_rows = await conn.fetch("""
        SELECT DISTINCT problem_id
        FROM submissions
        WHERE user_id = $1 AND status = 'Accepted' AND problem_id IS NOT NULL
    """, user_id)
    solved_problems = {f"problem_{row['problem_id']}" for row in solved_rows if row['problem_id'] is not None}

    # Fetch completed lessons
    lesson_rows = await conn.fetch("""
        SELECT DISTINCT lesson_id
        FROM lesson_progress
        WHERE user_id = $1 AND completed = true AND lesson_id IS NOT NULL
    """, user_id)
    completed_lessons = {f"lesson_{row['lesson_id']}" for row in lesson_rows if row['lesson_id'] is not None}

    await conn.close()
    # Return a set of all completed item IDs (matching Pinecone IDs)
    return solved_problems.union(completed_lessons)

def extract_keywords(topic):
    words = re.findall(r'\w+', topic.lower())
    keywords = [w for w in words if len(w) > 2]
    return keywords

async def suggest_next(user_id: str, user_input: str, user_level: str = "beginner", extra: dict = None):
    """
    Suggest the next problem or lesson for a user using Pinecone.
    Streams the result token by token, similar to generate_hint.
    Accepts extra context such as lessonId, problemId, or topic.
    """
    item_type = determine_item_type(user_input)
    completed_ids = await fetch_user_history(user_id)
    extra = extra or {}

    # Handle both lessonId and lesson_id
    lesson_id = extra.get("lessonId") or extra.get("lesson_id")
    problem_id = extra.get("problemId") or extra.get("problem_id")
    topic = extra.get("topic")

    # Build context string from extra info
    context_parts = []
    if lesson_id:
        context_parts.append(f"Related lesson id: {lesson_id}")
    if problem_id:
        context_parts.append(f"Related problem id: {problem_id}")
    if topic:
        context_parts.append(f"Topic: {topic}")
    context_str = "\n".join(context_parts)

    prompt = (
        f"User request: {user_input}\n"
        f"{context_str}\n"
        f"Suggest a {item_type} for a {user_level} user who has completed {len(completed_ids)} items."
    )

    # Map user_level to Pinecone difficulty
    level_to_difficulty = {
        "beginner": "easy",
        "intermediate": "medium",
        "advanced": "hard"
    }
    difficulty_order = ["easy", "medium", "hard"]

    # Infer current user difficulty
    inferred = await infer_user_difficulty(completed_ids)
    try:
        idx = difficulty_order.index(inferred)
        # Suggest next level if possible, else same level
        next_difficulty = difficulty_order[min(idx + 1, len(difficulty_order) - 1)]
    except ValueError:
        next_difficulty = "easy"

    # Use next_difficulty in your filter
    pinecone_filter = {
        "type": {"$eq": item_type},
        "difficulty": {"$eq": next_difficulty}
    }
    # if lesson_id:
    #     pinecone_filter["id"] = {"$eq": item_type + str(lesson_id)}


    query_embedding = get_embedding(prompt)
    results = index.query(
        vector=query_embedding,
        top_k=5,
        include_metadata=True,
        filter=pinecone_filter
    )
    # Find the first not-completed item
    selected = None
    for match in results["matches"]:
        item_id = match["id"]
        if item_id not in completed_ids:
            try:
                numeric_id = int(item_id.split("_")[1])
                # Include the title from metadata if available
                selected = {
                    "id": numeric_id,
                    "type": item_type,
                    "title": match["metadata"].get("title", "")
                }
                break
            except Exception:
                continue
    if not selected and results["matches"]:
        item_id = results["matches"][0]["id"]
        try:
            numeric_id = int(item_id.split("_")[1])
            selected = {
                "id": numeric_id,
                "type": item_type,
                "title": results["matches"][0]["metadata"].get("title", "")
            }
        except Exception:
            selected = None

    # Stream the result as JSON, token by token
    if selected:
        text = json.dumps(selected)
    else:
        text = "Sorry, no suitable problem or lesson found."
    for token in text:
        await asyncio.sleep(0)  # Yield control to event loop
        yield token

async def infer_user_difficulty(completed_ids):
    # Fetch metadata for completed items (you may need to batch this)
    difficulties = []
    for item_id in completed_ids:
        try:
            res = index.fetch(ids=[item_id])
            meta = res['vectors'][item_id]['metadata']
            if 'difficulty' in meta:
                difficulties.append(meta['difficulty'])
        except Exception:
            continue
    # Count and return the most common difficulty, or "easy" if none
    from collections import Counter
    if difficulties:
        most_common = Counter(difficulties).most_common(1)[0][0]
        return most_common
    return "easy"

def determine_item_type(user_input: str) -> str:
    """
    Determines whether to suggest a problem or a lesson based on user input.
    Returns "problem" or "lesson".
    """
    input_lower = user_input.lower()
    # If user asks for a problem related to a lesson/concept
    if "problem" in input_lower and ("lesson" in input_lower or "concept" in input_lower or "topic" in input_lower):
        return "problem"
    # Lesson keywords
    lesson_keywords = ["lesson", "learn", "theory", "tutorial", "concept", "explain"]
    if any(word in input_lower for word in lesson_keywords):
        return "lesson"
    # Problem keywords
    problem_keywords = ["problem", "challenge", "practice", "exercise", "task", "question"]
    if any(word in input_lower for word in problem_keywords):
        return "problem"
    # Default
    return "problem"
