# App test suite

Offline-by-default pytest smoke tests for the Streamlit app helpers.

```
cd app && python3 -m pip install -r requirements-dev.txt && python3 -m pytest tests -q
```

Tests that need live Bedrock/AWS are marked `@pytest.mark.live` and are skipped
offline. Pass `--run-live` to enable them:

```
cd app && python3 -m pytest tests -q --run-live
```
