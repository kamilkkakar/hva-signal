FROM python:3.12-slim

WORKDIR /hackathon/apps/api
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_MODE=replay
ENV HOSTED_LIVE_ENABLED=false
ENV HOSTED_LIVE_REAL_VENDOR_ENABLED=false
ENV DEMO_ALLOWANCE_ENABLED=false
ENV DEMO_ALLOWANCE_MAX_TOTAL_UNITS=0
ENV HVA_PUBLIC_CONTEXT=1
ENV HVA_PUBLIC_TEMPORAL_STORIES=1
ENV HVA_PUBLIC_TWO_SIGNAL=0
ENV HVA_PUBLIC_GEOGRAPHY=0
ENV HVA_PUBLIC_SAFETY_MIDDLEWARE=1
ENV OPERATOR_APPROVAL_ENABLED=false
ENV LOCAL_SQLITE_PERSISTENCE_ENABLED=false

COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
COPY apps/api/tests/fixtures ./tests/fixtures
COPY data/demo/phoenix /hackathon/data/demo/phoenix
COPY data/gate0 /hackathon/data/gate0
COPY data/phoenix/reference /hackathon/data/phoenix/reference
COPY data/areas /hackathon/data/areas
COPY data/context/phoenix-demo /hackathon/data/context/phoenix-demo
COPY data/context/cross-city /hackathon/data/context/cross-city
COPY data/acquisitions/cross-city /hackathon/data/acquisitions/cross-city
COPY data/phoenix/snapshots /hackathon/data/phoenix/snapshots
COPY scripts/build_gate0_expected_tile_coverage.py /hackathon/scripts/build_gate0_expected_tile_coverage.py
COPY scripts/gate0_between_aoi.py /hackathon/scripts/gate0_between_aoi.py
COPY scripts/gate0_static_field.py /hackathon/scripts/gate0_static_field.py
COPY scripts/gate0_static_field_audit.py /hackathon/scripts/gate0_static_field_audit.py
RUN pip install --no-cache-dir .

COPY apps/api/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/docker-entrypoint.sh"]
