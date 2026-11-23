FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml README.md main.py config.py ./
COPY app ./app
COPY helper_lib ./helper_lib
COPY scripts ./scripts
COPY prompts ./prompts
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# TODO [ERIK]: Add selected runtime dependencies and document mounts for model
# weights, data and index once ready. This image serves the scaffold only.
