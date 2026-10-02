FROM python:3.12-slim
WORKDIR /workspace

COPY deployment/backend/requirements.txt /tmp/requirements.txt
COPY deployment/backend/wheels /tmp/wheels
RUN pip install --no-index --find-links=/tmp/wheels -r /tmp/requirements.txt

COPY . /workspace

ENV PYTHONPATH=/workspace
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
