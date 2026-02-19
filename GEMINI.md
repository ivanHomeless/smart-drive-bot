# GEMINI.md: Project Overview and Development Guide

This document provides a comprehensive overview of the **CarQuery AI Bot** project, intended to be used as a quick-start guide and ongoing reference for developers.

## Project Overview

The CarQuery AI Bot is a Telegram bot built to streamline lead generation for a car dealership. It uses a conversational interface to guide users through structured dialogs for various services, such as buying, selling, or checking a car.

The bot integrates with **AmoCRM** to automatically create and update leads, and it leverages the **OpenAI API** to classify free-text user inquiries and pre-fill information in the dialogs.

### Core Technologies

- **Programming Language:** Python 3.12
- **Telegram Bot Framework:** `aiogram` 3.x
- **Database:** PostgreSQL (for users, leads, CRM tokens, and AI logs)
- **Database Migrations:** `alembic`
- **In-Memory Storage:** Redis (for FSM state management)
- **CRM Integration:** AmoCRM REST API
- **AI Integration:** OpenAI API (`gpt-4o-mini` with `gpt-4o` fallback)
- **Testing:** `pytest` and `pytest-asyncio`
- **Containerization:** Docker and Docker Compose

### Architecture

The application follows a modular structure:

- **`src/main.py`**: The main entry point, responsible for initializing the bot, dispatcher, database, and all services.
- **`src/bot/`**: Contains all `aiogram`-related components:
    - **`handlers/`**: Implements the conversation logic. A `BaseDialogHandler` provides a generic engine for creating multi-step dialogs.
    - **`states/`**: Defines the FSM (Finite State Machine) states for each conversation flow.
    - **`keyboards/`**: Builds the inline and reply keyboards for user interaction.
    - **`middlewares/`**: Handles cross-cutting concerns like database sessions, logging, and rate limiting.
- **`src/services/`**: Houses the business logic for interacting with external services:
    - **`amocrm/`**: A client for the AmoCRM API, including authentication and services for contacts, leads, and notes.
    - **`openai_client/`**: A client for the OpenAI API to classify user text.
    - **`lead_processor.py`**: Orchestrates the process of saving lead data to the database and sending it to AmoCRM.
- **`src/db/`**: Manages the database connection, models (`SQLAlchemy`), and data access layer (repositories).
- **`src/utils/`**: Contains helper functions for tasks like phone number validation and retry logic.
- **`tests/`**: Contains the test suite for the project.

## Building and Running

### Local Development

1.  **Set up the environment:**
    ```bash
    # Clone the repository
    git clone <repo-url>
    cd carquery-ai-bot

    # Create and activate a virtual environment
    python3.12 -m venv .venv
    source .venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt
    ```

2.  **Configure environment variables:**
    ```bash
    # Copy the example .env file
    cp .env.example .env

    # Edit the .env file with your credentials:
    # - TELEGRAM_BOT_TOKEN
    # - OPENAI_API_KEY
    # - ADMIN_CHAT_ID
    # Set AMOCRM_MOCK_MODE=true for development without a real AmoCRM account.
    ```

3.  **Run services and apply migrations:**
    ```bash
    # Start PostgreSQL and Redis
    docker compose up -d db redis

    # Apply database migrations
    .venv/bin/alembic upgrade head
    ```

4.  **Run the bot:**
    ```bash
    .venv/bin/python -m src.main
    ```

### Docker

To run the entire stack (bot, database, and Redis) using Docker:

1.  **Configure the `.env` file** as described above.
2.  **Build and run the containers:**
    ```bash
    docker compose up -d --build
    ```

### Testing

To run the test suite:

```bash
.venv/bin/pytest tests/
```

## Development Conventions

- **Modular Design:** The project is organized into distinct modules with clear responsibilities. New features should follow this pattern.
- **`BaseDialogHandler`:** When adding a new multi-step conversation, subclass `BaseDialogHandler` and define the steps and states. This will automatically register all the necessary handlers.
- **Dependency Injection:** Services like the `OpenAIClient` and `LeadProcessor` are injected into the `aiogram` dispatcher, making them available to handlers.
- **Configuration:** Application settings are managed through a `pydantic-settings` model in `src/config.py` and loaded from environment variables.
- **Testing:** The `tests/` directory mirrors the `src/` directory structure. New features should be accompanied by corresponding tests. The project uses `pytest` and `pytest-asyncio`.
