FROM python:3.14

WORKDIR /code

# Install UV into a system-wide path
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Verify UV installation
RUN /usr/local/bin/uv --version

# Copy only necessary files for installation
COPY pyproject.toml /code/
COPY README.md /code/
COPY app /code/app
# Copy test data for FAKE_CHECK_IN_TEST_MODE
COPY tests /code/tests

# Use UV to install dependencies
RUN /usr/local/bin/uv sync

# Run FastAPI with Uvicorn using UV - check which path works
CMD ["/usr/local/bin/uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9898"]