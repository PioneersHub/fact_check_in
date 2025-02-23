FROM python:3.12

WORKDIR /code

# Install UV (instead of Poetry)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files
COPY ./pyproject.toml /code/pyproject.toml

# Use UV to install dependencies (faster and more efficient)
RUN uv venv && uv pip install -r <(uv pip compile pyproject.toml --without-hashes)

# Copy the application code
COPY ./app /code/app

# Run FastAPI with Uvicorn using UV
CMD ["uv", "pip", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9898"]