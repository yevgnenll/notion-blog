# Blog Generator - AGENTS.md

## Project Overview

A blog generation agent that integrates NotebookLM (Google's AI notebook tool) with Notion and Telegram. The system receives questions via Telegram, queries NotebookLM for answers, uses OpenAI to refine and structure the response into a blog post, and publishes to Notion.

## Project Structure

```
blog-generator/
├── main.py               # Entry point - Starts FastAPI server
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (NOT KEY, DO NOT COMMIT)
├── README.md             # User documentation
├── AGENTS.md             # This file - Developer/Agent guide
├── server/               # FastAPI REST API
│   ├── __init__.py
│   ├── main.py           # FastAPI app initialization
│   └── routes/
│       ├── __init__.py
│       ├── blog.py       # Blog-related endpoints
│       └── telegram.py   # Telegram webhook handler
├── agent/                # Business logic layer
│   ├── __init__.py
│   ├── notebooklm.py     # NotebookLM integration (async)
│   └── brain.py          # OpenAI-based content composition
├── integrations/         # External API clients
│   ├── __init__.py
│   └── notion.py         # Notion Database client
└── utils/                # Utility functions
    ├── __init__.py
    └── config.py         # Environment and configuration management
```

## Environment Variables (.env)

Required variables:
- `OPENAI_API_KEY` - OpenAI API key for content generation
- `NOTION_INTEGRATION_KEY` - Notion integration token
- `NOTION_DATABASE_ID` - Notion database ID for blog posts
- `NOTION_DB_URL` - Full URL to Notion database page
- `TELEGRAM_BOT_KEY` - Telegram bot token
- `NOTEBOOKLM_NOTEBOOK_ID` - NotebookLM notebook ID (optional initially)

## Build & Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations/setup (if any)
# No migrations needed for this project
```

## Running the Application

```bash
# Start the FastAPI server
python main.py

# Server runs on http://0.0.0.0:8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Root endpoint |
| GET | /health | Health check |
| POST | /api/blog/query | Query NotebookLM and generate blog |
| POST | /api/blog/improve | Improve blog content |
| POST | /api/blog/generate | Generate blog from query |
| POST | /api/telegram/webhook | Telegram webhook handler |

## Telegram Bot Commands

- `/start` - Start the bot
- `/query <question>` - Ask NotebookLM and generate blog post

## Code Style Guidelines

### Python Style
- Use **Python 3.12+**
- Follow **PEP 8** naming conventions
- Use **type hints** for all function signatures
- Use **async/await** for I/O operations (NotebookLM, HTTP requests)
- Prefer **f-strings** over .format() or % formatting
- Use **single quotes** for strings by default

### Project-Specific Conventions

#### Naming
- **Classes**: PascalCase (e.g., `NotebookLMWrapper`, `BlogBrain`)
- **Functions/Variables**: snake_case (e.g., `load_notion_integration_key`)
- **Constants**: UPPERCASE (e.g., `CONFIG`, `DATA_DIR`)

#### Error Handling
- Use **try/except** blocks for external API calls
- Return descriptive error messages
- Wrap external API calls in utility functions
- Prefer returning `None` or empty dict/list over raising exceptions for recoverable errors

#### Imports
- Always use **absolute imports**
- Group imports: standard library → third-party → local
- Import specific classes/functions, not entire modules:
  ```python
  # ✅
  from notebooklm import NotebookLMClient
  from utils.config import CONFIG

  # ❌
  import notebooklm
  notebooklm.NotebookLMClient
  ```

#### Async/Await
- All NotebookLM methods must be `async`
- Use `async with self.client` pattern for resource management
- Convert async calls in sync contexts with `asyncio.run()`

#### Configuration
- Use `utils/config.py` for all configuration access
- Never hardcode sensitive values
- Keep `.env` in `.gitignore`

### File Organization

| Component | Location | Notes |
|-----------|----------|-------|
| API routes | `server/routes/` | One file per integration |
| Business logic | `agent/` | Core AI/LLM logic |
| External clients | `integrations/` | Notion, Telegram clients |
| Utilities | `utils/` | Shared helpers and config |

### Documentation
- Add **docstrings** to all public functions/classes
- Use **Google-style docstrings**:
  ```python
  def my_function(param: str) -> dict:
      """Short description.

      Args:
          param: Parameter description.

      Returns:
          Description of return value.
      """
  ```
- Update this file when adding new endpoints

### Testing
- No unit tests currently implemented
- Test endpoints with curl or Postman
- Test Telegram bot manually with sample messages

## LSP/Diagnostic Notes

- Type errors may appear for external libraries (notebooklm, notion-client)
- These are false positives due to incomplete type stubs
- Do not attempt to fix LSP errors for known external libraries
- Focus on runtime correctness rather than static type checking

## Key Dependencies

| Package | Purpose |
|---------|---------|
| notebooklm-py | Google NotebookLM interface |
| notion-client | Notion API client |
| fastapi | Web framework |
| openai | LLM for content refinement |
| python-telegram-bot | Telegram bot interface |

## Deployment Considerations

1. **Environment Variables**: Never commit `.env` file
2. **Data Directory**: `data/notebooklm_storage/` stores auth tokens
3. **Rate Limits**: Be mindful of Notion and OpenAI API rate limits
4. **Security**: Rotate API keys regularly, use environment-specific keys

## Contributing

1. Follow existing code structure
2. Add docstrings for new functions
3. Test with actual API calls before committing
4. Update this file when adding new features
