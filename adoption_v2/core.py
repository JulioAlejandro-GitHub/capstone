"""Pure, deterministic contracts; no database, filesystem mutation or ML imports."""

import hashlib
import json
import math
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = UUID("b65ecac4-a0f1-5c08-b897-b9cf68a108a6")
CONTRACT_HASH = "297a5d54f4dd1c9d6f16150a33eda200059eca7c91a96087d33a68a24077d54a"
MANIFEST_HASH = "f276f819aa8512492ed89a52f12d192c1ace6cde24eee967287d17cd5f05dd57"
CATALOG_HASH = "6df01a4d0e8fbcfd3e65a23e1394902097e565adad6b1b99de56a90f342cfa68"


class Blocked(ValueError):
    """Stable non-sensitive code and structural locator, never row contents."""

    def __init__(self, code, location=""):
        self.code, self.location = code, location
        super().__init__(f"{code}: {location}")


def require(condition, code, location=""):
    if not condition:
        raise Blocked(code, location)


def encode(value):
    if isinstance(value, Decimal):
        return {"$decimal": str(value)}
    if isinstance(value, UUID):
        return {"$uuid": str(value)}
    if isinstance(value, datetime):
        return {"$datetime": value.isoformat()}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, bytes):
        return {"$bytes": value.hex()}
    if isinstance(value, dict):
        # Tag dictionaries too, so user JSON containing "$decimal" cannot collide.
        return {"$object": [[k, encode(v)] for k, v in sorted(value.items())]}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    if isinstance(value, float):
        require(math.isfinite(value), "NONFINITE_SOURCE_NUMBER")
    return value


def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if isinstance(value, dict):
        require(len(value) == 1, "INVALID_ARCHIVE_ENCODING")
        k, v = next(iter(value.items()))
        converters = {
            "$decimal": Decimal,
            "$uuid": UUID,
            "$datetime": datetime.fromisoformat,
            "$date": date.fromisoformat,
            "$bytes": bytes.fromhex,
        }
        if k == "$object":
            require(len(v) == len({x[0] for x in v}), "DUPLICATE_ARCHIVE_KEY")
            return {a: decode(b) for a, b in v}
        require(k in converters, "INVALID_ARCHIVE_ENCODING")
        return converters[k](v)
    return value


def canonical(value):
    return json.dumps(
        encode(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def stable_id(kind, identity):
    return str(uuid5(NAMESPACE, kind + ":" + canonical(identity)))


@lru_cache(maxsize=1)
def contract():
    path = ROOT / "adoption_v2/legacy_contract.json"
    require(
        hashlib.sha256(path.read_bytes()).hexdigest() == CONTRACT_HASH,
        "LEGACY_CONTRACT_CHANGED",
    )
    return json.loads(path.read_text())


def target():
    from alembic_v2.resources import load_baseline

    path = ROOT / "alembic_v2/baseline/catalog_manifest.json"
    require(
        hashlib.sha256(path.read_bytes()).hexdigest() == MANIFEST_HASH,
        "CERTIFIED_BASELINE_CHANGED",
    )
    return load_baseline()


def row_key(table, row):
    names = contract()["primary_keys"][table]
    require(
        all(row.get(k) is not None for k in names), "SOURCE_PRIMARY_KEY_MISSING", table
    )
    return tuple(str(row[k]) for k in names)


def table_digest(rows):
    return digest(sorted(rows, key=canonical))


def number(value, location, integer=False):
    require(type(value) in (int, float, Decimal), "STRICT_NUMBER_REQUIRED", location)
    n = Decimal(str(value))
    require(n.is_finite(), "NONFINITE_NUMBER", location)
    if integer:
        require(
            n == n.to_integral_value() and type(value) is not float,
            "INTEGER_REQUIRED",
            location,
        )
    return n


def path_get(value, path):
    try:
        for key in path:
            value = value[key]
    except (KeyError, TypeError, IndexError):
        raise Blocked("EVIDENCE_PATH_MISSING", ".".join(map(str, path))) from None
    return value


class Evidence:
    """Only references to captured source rows or explicitly approved documents.

    Documents have raw bytes/hash and are pinned by the D authorization. They
    provide reviewed provenance, never implicit defaults or filenames as data.
    """

    def __init__(self, rows, documents):
        self.rows, self.documents = rows, {}
        for name, item in documents.items():
            require(sha(item["raw"]) == item["sha256"], "DOCUMENT_HASH_MISMATCH", name)
            self.documents[name] = json.loads(item["raw"])

    def get(self, ref):
        require(
            isinstance(ref, dict)
            and set(ref) in ({"table", "key", "path"}, {"document", "path"}),
            "EVIDENCE_REFERENCE_REQUIRED",
        )
        if "document" in ref:
            require(ref["document"] in self.documents, "DOCUMENT_MISSING")
            return path_get(self.documents[ref["document"]], ref["path"])
        table = ref["table"]
        require(table in self.rows, "SOURCE_TABLE_MISSING", table)
        rows = [r for r in self.rows[table] if row_key(table, r) == tuple(ref["key"])]
        require(len(rows) == 1, "EVIDENCE_CARDINALITY", table)
        return path_get(rows[0], ref["path"])
