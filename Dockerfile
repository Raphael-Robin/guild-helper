FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy the rest of the project
COPY . .

CMD ["uv", "run", "python", "-m", "src.DiscordBot.main"]
```

---

**Update `.dockerignore`** to exclude uv's local cache:
```
.env
.venv
__pycache__
*.pyc
.git
.python-version