from pathlib import Path

from scripts.check_policy import validate


def test_seed_policy_is_valid_but_untrusted():
    root = Path(__file__).parents[3]
    policy = validate(root / "examples" / "team-todo" / "aware.yaml")
    assert policy == {"safety_class": "unclassified", "confirmation_policy": "unresolved"}

