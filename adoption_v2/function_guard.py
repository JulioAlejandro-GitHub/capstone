"""D-04 function preflight: exact native entries and dependency membership."""

import hashlib
import json

from .core import ROOT, contract, require

DEPENDENCY_HASH = "af105f1a6a40b24a1beb7c758e77007d80db818417cc92277cd66fa87c4478bf"
DEPENDENCY_SQL = """SELECT p.proname AS name,
    pg_get_function_identity_arguments(p.oid) AS arguments,
    d.deptype,d.objsubid,d.refclassid::regclass::text AS referenced_catalog,
    pg_describe_object(d.refclassid,d.refobjid,d.refobjsubid) AS referenced_object
    FROM pg_proc p JOIN pg_depend d ON d.classid='pg_proc'::regclass AND d.objid=p.oid
    WHERE p.pronamespace='public'::regnamespace
    ORDER BY 1,2,3,4,5,6"""


def dependency_reference():
    path = ROOT / "docs/audits/e10_10_5d3_evidence/route_a_function_dependencies.json"
    raw = path.read_bytes()
    require(
        hashlib.sha256(raw).hexdigest() == DEPENDENCY_HASH,
        "FUNCTION_DEPENDENCY_CERTIFICATE_CHANGED",
    )
    return json.loads(raw)["dependencies"]


def check_functions(observed, certified, dependencies, expected_dependencies):
    """Legacy restore ACL is NULL (--no-acl); delta later installs exact v2 ACL.

    Extension entries have no ACL exception: every field equals certified Ruta A.
    Membership comes from pg_depend/pg_extension, not an allowlist of names.
    """
    key = lambda r: (r["name"], r["arguments"])
    own = {
        (r["name"], r["arguments"])
        for r in contract()["expected_schema"]["functions"]
        if not r["extension_owned"]
    }
    reference = {key(r): r for r in certified}
    require(len(reference) == len(certified), "DUPLICATE_CERTIFIED_FUNCTION")
    extensions = {key(r) for r in certified if r["extension"] is not None}
    require(
        len(extensions) == 36
        and all(reference[k]["extension"] == "pgcrypto" for k in extensions),
        "EXTENSION_FUNCTION_CONTRACT_CHANGED",
    )
    require(
        own.isdisjoint(extensions) and own <= reference.keys(),
        "OWN_FUNCTION_CONTRACT_CHANGED",
    )
    actual = {key(r): r for r in observed}
    require(len(actual) == len(observed), "DUPLICATE_SOURCE_FUNCTION")
    require(actual.keys() == own | extensions, "FUNCTION_INVENTORY_MISMATCH")
    for k in sorted(own):
        expected = dict(reference[k])
        require(
            expected["owner"] == "capstone_v2_migrator"
            and expected["extension"] is None,
            "OWN_FUNCTION_CONTRACT_CHANGED",
        )
        # Exact pre-adoption ACL of the isolated no-ACL restore; not ignored.
        expected["proacl"] = None
        require(actual[k] == expected, "OWN_FUNCTION_CONTRACT_MISMATCH", k[0])
    for k in sorted(extensions):
        require(actual[k] == reference[k], "EXTENSION_FUNCTION_CONTRACT_MISMATCH", k[0])
    wanted = [r for r in expected_dependencies if key(r) in own | extensions]
    require(dependencies == wanted, "FUNCTION_DEPENDENCY_MISMATCH")
