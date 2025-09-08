from app.family.context import ensure_seed
import scripts.export_family_conversations as convo


def test_each_generator_yields_at_least_one_sample():
    ensure_seed()
    empty = []
    for gen in convo.GENERATORS:
        produced = list(gen())
        assert produced, f"generator {gen.__name__} produced no samples"
        empty.extend(produced)
    # basic shape check
    first = empty[0]
    assert 'messages' in first and isinstance(first['messages'], list)
