FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
RUN python -m pip install --no-cache-dir . && useradd --create-home --uid 10001 agent && mkdir /data && chown agent:agent /data
USER agent
ENV DATABASE_PATH=/data/voice_agent.db CRM_DATABASE_PATH=/data/crm.db
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
