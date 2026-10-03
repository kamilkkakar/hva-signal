import httpx
import pytest
from app.integrations.fortyguard.client import FortyGuardHttpClient
from app.integrations.fortyguard.exceptions import FortyGuardHttpError

@pytest.mark.parametrize('body,balance', [({'credit_summary': {'cycle_remaining_credits': 2000000}}, 2000000), ({'data': {'credit_summary': {'total_remaining_credits': 125.5}}}, 125.5), ({'credit_summary': {'cycle_remaining_credits': 0}}, 0)])
def test_usage_balance(body, balance):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=body)
    with FortyGuardHttpClient('test-secret', transport=httpx.MockTransport(handler)) as client:
        assert client.remaining_credits() == balance
        assert client.submission_count == 0
        assert requests[0].url.path == '/v1/system/fetch-api-key-usage'

@pytest.mark.parametrize('body', [None, [], {'data': None}, {'credit_summary': {'cycle_remaining_credits': True}}, {'credit_summary': {'cycle_remaining_credits': -1}}, {'credit_summary': {'cycle_remaining_credits': '2000000'}}])
def test_invalid_usage_unknown(body):
    with FortyGuardHttpClient('test-secret', transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))) as client:
        with pytest.raises(FortyGuardHttpError):
            client.remaining_credits()

def test_usage_error_redacted():
    with FortyGuardHttpClient('test-secret', transport=httpx.MockTransport(lambda request: httpx.Response(401, text='test-secret'))) as client:
        with pytest.raises(FortyGuardHttpError) as error:
            client.remaining_credits()
        assert 'test-secret' not in str(error.value)
