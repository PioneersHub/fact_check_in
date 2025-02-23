FROM python:3.12

WORKDIR /code

# Install UV properly and move it to a system-wide path
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv ~/.local/bin/uv /usr/local/bin/uv

# Verify UV installation
RUN /usr/local/bin/uv --version

# Copy project files
COPY . /code

# Use UV to install dependencies
RUN /usr/local/bin/uv venv && \
    /usr/local/bin/uv pip compile pyproject.toml -o requirements.txt && \
    /usr/local/bin/uv pip install -r requirements.txt

# Copy the application code
COPY ./app /code/app

# Run FastAPI with Uvicorn using UV
CMD ["/code/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9898"]