import json


def test_normalize_pedalboard_chain_effects_list_to_kwargs():
    # Import locally to avoid importing Flask app as a test side-effect beyond module import
    from aiagent import _normalize_audioengine_plan

    plan = {
        "calls": [
            {
                "op": "pedalboard_chain",
                "args": {
                    "effects": [
                        {"name": "reverb", "args": {"room_size": 0.4}},
                        {"name": "distortion", "args": {"drive_db": 12}},
                        {"name": "not_supported", "args": {"x": 1}},
                    ]
                },
            }
        ]
    }

    normalized = _normalize_audioengine_plan(json.loads(json.dumps(plan)))

    assert normalized is not None
    assert normalized["calls"][0]["op"] == "pedalboard_chain"

    args = normalized["calls"][0]["args"]
    assert "effects" not in args
    assert args["reverb"]["room_size"] == 0.4
    assert args["distortion"]["drive_db"] == 12
    assert "not_supported" not in args

