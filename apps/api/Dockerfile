FROM python:3.12-slim

WORKDIR /hackathon/apps/api
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_MODE=replay

COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
COPY apps/api/tests/fixtures ./tests/fixtures
COPY data/demo/phoenix /hackathon/data/demo/phoenix
COPY data/phoenix/reference /hackathon/data/phoenix/reference
COPY data/areas /hackathon/data/areas
RUN pip install --no-cache-dir .

COPY apps/api/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/docker-entrypoint.sh"]
