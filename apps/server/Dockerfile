FROM python:3.12-slim
WORKDIR /srv
COPY apps/server /srv/apps/server
COPY fixtures /srv/fixtures
RUN pip install --no-cache-dir /srv/apps/server && useradd --uid 10001 --create-home widget
USER widget
ENV PYTHONPATH=/srv/apps/server
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
