FROM python:3.12

WORKDIR /code

# Install UV properly and move it to a system-wide path
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv ~/.local/bin/uv /usr/local/bin/uv

# Verify UV installation
RUN /usr/local/bin/uv --version

# Copy only necessary files for installation
COPY pyproject.toml /code/
COPY README.md /code/
COPY app /code/app
COPY event_config.yml /code/event_config.yml
# Copy test data for FAKE_CHECK_IN_TEST_MODE
COPY tests /code/tests

# Use UV to install dependencies
RUN /usr/local/bin/uv venv && \
    /usr/local/bin/uv pip install -e .

# Run FastAPI with Uvicorn using UV - check which path works
CMD ["/usr/local/bin/uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9898"]