from app.modules.API_monitor.json_matcher import json_matches

print(
    json_matches(
        {"id": 1},
        {"id": 1, "name": "Alice"},
    )
)
# Expected: True

print(
    json_matches(
        {"id": 1},
        {"id": 2},
    )
)
# Expected: False

print(
    json_matches(
        {"user": {"id": 5}},
        {"user": {"id": 5, "name": "Bob"}},
    )
)
# Expected: True

print(
    json_matches(
        {"user": {"id": 5}},
        {"user": {"id": 7}},
    )
)
# Expected: False