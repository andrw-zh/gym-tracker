# Dev image to build the project. This image is not intended to be used in production.
FROM python:3.12 AS builder

# set explicit working directory
WORKDIR /app  

# Create a virtual environment to isolate dependencies from the system Python.
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install -r requirements.txt

# Runtime stage: minimal, no shell, no pip, non-root
FROM python:3.12-slim

WORKDIR /app

# Copy the virtual environment from the builder stage to the runtime stage.
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy the application code into the container.
COPY sourcing.py .

ENTRYPOINT ["/venv/bin/python", "sourcing.py"]