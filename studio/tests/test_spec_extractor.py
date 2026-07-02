from studio.spec_extractor import extract_spec

VALID = '''Here is the design.
```spec
{"plugin": {"name": "demo"}, "components": []}
```
Anything after.'''

def test_extracts_valid_spec_block():
    out = extract_spec(VALID)
    assert out == {"plugin": {"name": "demo"}, "components": []}

def test_absent_block_returns_none():
    assert extract_spec("no fenced block here") is None

def test_malformed_json_returns_none():
    assert extract_spec("```spec\n{not json}\n```") is None

def test_missing_plugin_name_returns_none():
    assert extract_spec('```spec\n{"plugin": {}, "components": []}\n```') is None

def test_components_must_be_list():
    assert extract_spec('```spec\n{"plugin": {"name": "x"}, "components": {}}\n```') is None

def test_takes_last_block_when_multiple():
    text = ('```spec\n{"plugin": {"name": "old"}, "components": []}\n```\n'
            '```spec\n{"plugin": {"name": "new"}, "components": []}\n```')
    assert extract_spec(text)["plugin"]["name"] == "new"

def test_json_fence_fallback():
    assert extract_spec('```json\n{"plugin": {"name": "x"}, "components": []}\n```') == \
        {"plugin": {"name": "x"}, "components": []}
