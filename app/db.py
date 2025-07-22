import os
import asyncpg

PGUSER = os.getenv("PGUSER", "thangbui")
PGPASSWORD = os.getenv("PGPASSWORD", "password")
PGDATABASE = os.getenv("PGDATABASE", "gami-ai")
PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgres://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
)

async def save_ai_assistance(
    user_id=None,
    lesson_id=None,
    problem_id=None,
    session_id=None,
    user_query="",
    ai_response="",
    suggestion_type="",
):
    lesson_id = int(lesson_id) if lesson_id is not None else None
    user_id = int(user_id) if user_id is not None else None
    problem_id = int(problem_id) if problem_id is not None else None
    if lesson_id is None and problem_id is None:
        return
    conn = await asyncpg.connect(dsn=DATABASE_URL)
    await conn.execute(
        """
        INSERT INTO ai_assistance (user_id, lesson_id, problem_id, session_id, user_query, ai_response, suggestion_type, date_time)
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        """,
        user_id, lesson_id, problem_id, session_id, user_query, ai_response, suggestion_type
    )
    await conn.close()

async def fetch_previous_conversations(lesson_id: int, problem_id: int, session_id: str, user_id: int, limit: int = 5):
    if session_id is not None:
        query = """
            SELECT user_query, ai_response
            FROM ai_assistance
            WHERE session_id = $1
            ORDER BY date_time DESC
            LIMIT $2
        """
        params = (session_id, limit)
    elif user_id is not None and (lesson_id is not None or problem_id is not None):
        query = """
            SELECT user_query, ai_response
            FROM ai_assistance
            WHERE user_id = $1
            AND (
                (lesson_id = $2 AND $2 IS NOT NULL)
                OR
                (problem_id = $3 AND $3 IS NOT NULL)
            )
            ORDER BY date_time DESC
            LIMIT $4
        """
        params = (user_id, lesson_id, problem_id, limit)
    else:
        return []

    conn = await asyncpg.connect(dsn=DATABASE_URL)
    rows = await conn.fetch(query, *params)
    await conn.close()
    return list(reversed(rows))

async def get_solution_code(problem_id: int) -> str:
    conn = await asyncpg.connect(dsn=DATABASE_URL)
    row = await conn.fetchrow("SELECT solution_code FROM problems WHERE id=$1", problem_id)
    await conn.close()
    return row["solution_code"] if row else ""

async def get_testcases(problem_id: int):
    conn = await asyncpg.connect(dsn=DATABASE_URL)
    rows = await conn.fetch("SELECT id, input FROM test_cases WHERE problem_id=$1", problem_id)
    await conn.close()
    # Adapt this to your actual schema
    return [{"input": row["input"], "id": row["id"]} for row in rows]