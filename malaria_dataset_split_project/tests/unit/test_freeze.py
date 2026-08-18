from malaria_split.governance.freeze import _canonical_digest


def test_canonical_fingerprint_is_deterministic_and_order_sensitive():
    rows = [("a", "b", 1), ("c", None, 2)]
    assert _canonical_digest(rows) == _canonical_digest(list(rows))
    assert _canonical_digest(rows) != _canonical_digest(list(reversed(rows)))
