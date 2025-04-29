Description: README file for the SuperMean Backend Service.

# SuperMean Backend

This directory contains the Python FastAPI backend service for the SuperMean project. It handles the core logic for AI agents, skills, memory, orchestration, and communication with the frontend via API endpoints.

## Features

*   Modular Agent Architecture (SuperAgent, Specialized Agents)
*   Plug-and-Play Skills Library
*   Multi-Model Support (Gemini, DeepSeek, RouterAPI, etc.)
*   Persistent Memory System
*   Event-Driven Orchestration
*   FastAPI-based REST API for frontend interaction

## Project Structure
Use code with caution.
Markdown
backend/
├── agents/ # Specialized agents (Dev, Research, Design, Medical, etc.)
├── api/ # FastAPI endpoints, schemas, controllers
├── memory/ # Memory modules (Agent, Global, Vector)
├── models/ # LLM connectors and model router
├── orchestrator/ # Event bus, mission control, collaboration
├── skills/ # Reusable skill modules
├── super_agent/ # Meta-agent components (Planner, Builder, Evaluator)
├── utils/ # Shared utilities (logging, config, error handling)
├── .env.template # Template for environment variables
├── .gitignore # Git ignore rules
├── README.md # This file
├── requirements.txt # Python dependencies
└── run.py # Script to run the application

## Setup Instructions

1.  **Navigate to Backend Directory:**
    ```bash
    cd backend
    ```

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment.
    ```bash
    python -m venv venv
    ```

3.  **Activate the Virtual Environment:**
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Environment Variables

The application uses environment variables for configuration, especially for API keys and other sensitive settings.

1.  **Create a `.env` file:**
    Copy the template file:
    ```bash
    cp .env.template .env
    ```

2.  **Edit `.env`:**
    Open the `.env` file in your editor and fill in the required values (like API keys for Gemini, SerpApi, etc.).

    ```dotenv
    # Example .env content
    LOG_LEVEL=INFO
    ENVIRONMENT=development

    # API Keys (replace with your actual keys)
    GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
    SERPAPI_KEY=YOUR_SERPAPI_KEY_HERE
    # DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY_HERE # Add if applicable
    # ROUTERAPI_KEY=YOUR_ROUTERAPI_KEY_HERE     # Add if applicable

    # Other configurations can be added here
    ```

## Running the Service (Development)

Once the setup is complete and the `.env` file is configured, you can run the FastAPI development server using Uvicorn:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
Use code with caution.
api.main:app: Points to the FastAPI app instance in the api/main.py file.

--reload: Enables auto-reload when code changes (useful for development).

--host 0.0.0.0: Makes the server accessible on your local network.

--port 8000: Specifies the port to run on.

You should see output indicating the server is running, typically like:
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO: Started reloader process [...]
INFO: Started server process [...]
INFO: Waiting for application startup.
INFO: Application startup complete.

You can access the API documentation (Swagger UI) by navigating to http://localhost:8000/docs in your web browser.