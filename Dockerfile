# Choose a python base image
FROM python:3.12-slim

# Add user to do not run as root
RUN useradd -m botuser

# Set the working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy the rest of the project
COPY . .

# Change owner
RUN chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Set environment variable to ensure output is not buffered
ENV PYTHONUNBUFFERED=1

# Command to run the bot
CMD ["uv", "run", "python", "-m", "src.DiscordBot.main"]