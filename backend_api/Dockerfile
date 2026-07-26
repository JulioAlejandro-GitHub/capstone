FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system capstone && adduser --system --ingroup capstone capstone
COPY backend_api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend_api/app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
RUN mkdir -p /app/var/storage /app/var/artifacts && chown -R capstone:capstone /app
USER capstone
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
