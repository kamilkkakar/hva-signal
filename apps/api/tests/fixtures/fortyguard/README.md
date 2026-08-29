# Replay fixtures live under `apps/api/tests/fixtures/fortyguard` after sanitization.
# Do not commit raw FortyGuard responses from `workforce/context`.
#
# Generate:
#   python scripts/sanitize_fortyguard_fixture.py
#
# tcm tile temperatures in these fixtures are Celsius.
# Fixtures must never contain `api-key` / `api_key` / Authorization fields.
