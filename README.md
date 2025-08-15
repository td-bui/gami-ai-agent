# Gami-AI Agent Service

This project is a FastAPI-based backend service that provides a suite of AI-powered agents for a gamified programming education platform. It uses an orchestrator to intelligently route user requests to specialized agents, delivering contextual help, feedback, and personalized content recommendations.

## Features

-   **Agent-Based Architecture**: An orchestrator (`orchestrator.py`) analyzes user input and conversation history to select the most appropriate agent for the task.
-   **Specialized AI Agents**:
    -   **`explain`**: Provides clear, concise explanations of Python concepts.
    -   **`hint`**: Offers step-by-step hints for coding problems, including an optional code execution step to provide feedback on the user's current attempt.
    -   **`feedback`**: Delivers targeted feedback on a user's code submission for a specific problem.
    -   **`suggest_problem`**: A Retrieval-Augmented Generation (RAG) agent that uses Pinecone to recommend the next lesson or problem based on user history, level, and context.
    -   **`gamified_tuner`**: A Reinforcement Learning (Q-learning) agent that adapts the learning experience by suggesting actions like changing difficulty or offering motivation.
    -   **`conversation`**: Handles general conversational interactions and chit-chat.
-   **LLM Integration**: Leverages OpenAI's GPT models for natural language understanding and generation.
-   **Vector Database**: Integrates with Pinecone for fast and scalable semantic search to power content recommendations.
-   **Database Connectivity**: Connects to a PostgreSQL database using `asyncpg` to persist conversation history and retrieve user data.
-   **Secure API**: Endpoints are protected using JWT authentication.
-   **Containerized**: Includes a `Dockerfile` for easy and consistent deployment.

## Project Structure

```
gami-ai-agent/
├── Dockerfile
├── requirements.txt
├── q_table.pkl         # Saved state for the Gamified Tuner agent
└── app/
    ├── main.py         # FastAPI application, endpoints, and middleware
    ├── orchestrator.py # Core routing logic to select the appropriate agent
    ├── llm.py          # Wrapper for OpenAI API calls
    ├── db.py           # Asynchronous database functions
    └── agents/
        ├── conversation.py
        ├── explain.py
        ├── feedback.py
        ├── gamified_tuner.py
        ├── hint.py
        └── suggest_problem.py
```

## Setup and Installation

### 1. Prerequisites

-   Python 3.11+
-   PostgreSQL Database
-   Access to OpenAI and Pinecone APIs

### 2. Clone the Repository

```bash
git clone https://github.com/td-bui/gami-ai-agent.git
cd gami-ai-agent
```

### 3. Set up Environment

It is recommended to use a virtual environment.

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the root directory and add the following variables.

```env
# OpenAI Configuration
OPENAI_API_KEY="your-openai-api-key"

# Pinecone Configuration
PINECONE_API_KEY="your-pinecone-api-key"
PINECONE_ENV="your-pinecone-environment" # e.g., us-east-1
PINECONE_INDEX="gami-ai"

# PostgreSQL Database Configuration
PGDATABASE="gami-ai"
PGUSER="your-db-user"
PGPASSWORD="your-db-password"
PGHOST="localhost"
PGPORT="5432"

# JWT Secret (generate a secure base64 encoded key)
# python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
JWT_SECRET="your-base64-encoded-jwt-secret"

# URL for the separate code execution service
EXEC_API_BASE="http://localhost:8001"

# CORS Allowed Origins (comma-separated)
ALLOW_ORIGINS="http://localhost:3000,https://your-frontend-domain.com"
```

### 6. Run the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

The service will be available at `http://localhost:4000`.

## Running with Docker

### 1. Build the Docker Image

```bash
docker build -t gami-ai-agent .
```

### 2. Run the Docker Container

You can pass the environment variables from your `.env` file.

```bash
docker run -d --env-file .env -p 4000:4000 --name gami-ai-agent-container gami-ai-agent
```

## API Endpoints

-   `POST /api/ai/orchestrate`: The main endpoint for all conversational AI interactions. It accepts user input and context, routes to the appropriate agent, and streams the response.
-   `POST /api/ai/feedback`: Provides feedback for a given code submission against a problem description.
-   `POST /api/ai/tuner-step`: An endpoint for the `GamifiedTunerAgent` to process user action logs and determine the