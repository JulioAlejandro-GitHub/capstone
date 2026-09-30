"""Static contracts only: no PostgreSQL, Docker, training or application imports."""

import copy
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from pglast import ast, parse_sql
from pglast.enums import A_Expr_Kind, BoolExprType, ConstrType, NullTestType

from alembic_v2.resources import BASELINE, load_baseline
from alembic_v2.safety import (
    LABEL,
    UnsafeTarget,
    read_authorization,
    validate_docker_snapshot,
    validate_server_snapshot,
)
from scripts.db.build_dbv22_baseline import artifacts
from scripts.db.validate_v2_static import catalogue, validate, norm


def expression(node, row):
    """Small, explicit three-valued evaluator for scope/provenance AST tests only.

    Deliberately NOT an emulator for PostgreSQL or a substitute for stage B.
    Unsupported syntax raises rather than being treated as a passing check.
    """
    if isinstance(node, ast.A_Const):
        if node.isnull:
            return None
        if isinstance(node.val, ast.String):
            return node.val.sval
        if isinstance(node.val, ast.Integer):
            return node.val.ival
        raise AssertionError(node)
    if isinstance(node, ast.ColumnRef):
        return row.get(node.fields[-1].sval)
    if isinstance(node, ast.TypeCast):
        return expression(node.arg, row)
    if isinstance(node, ast.A_ArrayExpr):
        return [expression(v, row) for v in node.elements]
    if isinstance(node, ast.NullTest):
        value = expression(node.arg, row)
        return (
            (value is None)
            if node.nulltesttype == NullTestType.IS_NULL
            else (value is not None)
        )
    if isinstance(node, ast.FuncCall):
        values = [expression(v, row) for v in node.args]
        name = node.funcname[-1].sval
        if any(v is None for v in values):
            return None
        if name == "btrim":
            return values[0].strip()
        if name == "length":
            return len(values[0])
        raise AssertionError(name)
    if isinstance(node, ast.BoolExpr):
        values = [expression(v, row) for v in node.args]
        if node.boolop == BoolExprType.AND_EXPR:
            return False if False in values else (None if None in values else True)
        if node.boolop == BoolExprType.OR_EXPR:
            return True if True in values else (None if None in values else False)
        assert node.boolop == BoolExprType.NOT_EXPR
        return None if values[0] is None else not values[0]
    if isinstance(node, ast.A_Expr):
        left = expression(node.lexpr, row)
        op = node.name[0].sval
        if node.kind == A_Expr_Kind.AEXPR_IN:
            right = [expression(x, row) for x in node.rexpr]
            result = None if left is None else left in right
            return result if op == "=" or result is None else not result
        right = expression(node.rexpr, row)
        if node.kind == A_Expr_Kind.AEXPR_OP_ANY:
            return None if left is None else left in right
        if left is None or right is None:
            return None
        if op == "=":
            return left == right
        if op == "<>":
            return left != right
        if op == ">":
            return left > right
        if op == "~":
            return re.search(right, left) is not None
        raise AssertionError(op)
    raise AssertionError(type(node).__name__)


class StaticBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.statements = load_baseline()
        cls.catalogue = catalogue(cls.statements)

    def test_e01_revision_acl_is_select_only(self):
        acl = (BASELINE / "10_privileges.sql").read_text()
        statements = [s.strip() for s in acl.split(";") if "public.alembic_version" in s]
        self.assertEqual(statements, [
            "REVOKE ALL PRIVILEGES ON TABLE public.alembic_version FROM PUBLIC, capstone_v2_runtime",
            "GRANT SELECT ON TABLE public.alembic_version TO capstone_v2_runtime",
        ])

    def test_e03_exact_role_set_and_e04_preserved_resources(self):
        constraint = self.catalogue["constraints"][
            ("evaluations", "v2_evaluations_check_28938a6edbaa")
        ]
        allowed = {"training_validation_final", "calibration_default", "calibration_selected"}
        for role in allowed | {"development", "final_test", "external_complementary", "unknown", ""}:
            with self.subTest(role=role):
                self.assertEqual(expression(constraint.raw_expr, {
                    "source_kind": "e10", "evaluation_role": role,
                }), role in allowed)
        root = Path(__file__).resolve().parents[2]
        # DBV2.1 changes other objects explicitly; E-04 itself stays exact.
        for raw in parse_sql((root / "alembic_v2/e04_contract.sql").read_text()):
            node = raw.stmt
            if isinstance(node, ast.CreateFunctionStmt):
                actual = self.catalogue['functions']['.'.join(x.sval for x in node.funcname)]
            elif isinstance(node, ast.CreateTrigStmt):
                actual = self.catalogue['triggers'][node.relation.relname, node.trigname]
            elif isinstance(node, ast.IndexStmt):
                actual = self.catalogue['indexes'][node.idxname]
            elif isinstance(node, ast.AlterTableStmt):
                for cmd in node.cmds:
                    self.assertEqual(norm(self.catalogue['constraints'][node.relation.relname, cmd.def_.conname]), norm(cmd.def_))
                continue
            else:
                self.fail(type(node).__name__)
            self.assertEqual(norm(actual), norm(node))

    def test_e04_deferred_link_and_scientific_identity(self):
        constraints = self.catalogue['constraints']
        link = [v for (t, _), v in constraints.items() if t == 'evaluations'
                and v.contype == ConstrType.CONSTR_FOREIGN
                and [a.sval for a in v.fk_attrs] == ['calibration_id']]
        self.assertEqual(len(link), 1)
        self.assertTrue(link[0].deferrable and link[0].initdeferred)
        statement = next(s for s in self.statements if 'CREATE UNIQUE INDEX uq_e04_contract_role' in s)
        self.assertIn('NULLS NOT DISTINCT', statement)
        self.assertNotIn('threshold', statement)
        self.assertNotIn('source_record_key', statement)
        self.assertEqual(self.manifest['e04_contract_sha256'], __import__('hashlib').sha256(
            (BASELINE.parent / 'e04_contract.sql').read_bytes()).hexdigest())

    def test_d03_identity_and_exact_default_scope(self):
        root = Path(__file__).resolve().parents[2]
        previous = json.loads(
            (
                root
                / "docs/audits/e10_10_5d2_evidence/previous_baseline/catalog_manifest.json"
            ).read_text()
        )
        inventory = json.loads(
            (
                root / "docs/audits/e10_10_5d1_evidence/default_inventory.json"
            ).read_text()
        )
        approved = {
            (r["table"], r["column"])
            for r in inventory["rows"]
            if r["v2_resolved_function"]
        }
        old = {
            (e["name"], k): v
            for e in previous["statements"]
            if e["kind"] == "table"
            for k, v in e["columns"].items()
        }
        new = {
            (e["name"], k): v
            for e in self.manifest["statements"]
            if e["kind"] == "table"
            for k, v in e["columns"].items()
        }
        # DBV2.1 removes historical tables/columns and the fixed recall default.
        changed = {k for k in old.keys() & new.keys()
                   if old[k]["default"] != new[k]["default"]
                   and k != ("run_configurations", "clinical_target_recall")}
        self.assertEqual(changed, approved - {("model_governance_backfill_audit", "id")})
        self.assertEqual(len(changed), 38)
        for k in changed:
            self.assertEqual(new[k]["default"], "pg_catalog.gen_random_uuid()")
        identities = {k: v["identity"] for k, v in new.items() if v["identity"]}
        self.assertEqual(identities, {("experiment_execution_events", "id"): "a"})
        self.assertFalse(
            any(
                e["kind"] in ("sequence", "sequence_ownership")
                for e in self.manifest["statements"]
            )
        )
        self.assertEqual(
            self.manifest["identity_sequences"][0]["sequence"],
            "experiment_execution_events_id_seq",
        )

    def test_integral_catalogue_and_historical_contracts(self):
        result = validate()
        self.assertEqual(result["physical_tables_including_alembic"], 105)
        self.assertTrue(result["approved_contract_exact_match"])
        self.assertEqual(result["application_tables"], 104)

    def test_frozen_generation_is_reproducible(self):
        for name, content in artifacts().items():
            self.assertEqual((BASELINE / name).read_bytes(), content, name)

    def test_tampered_resource_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "baseline"
            shutil.copytree(BASELINE, dest)
            p = dest / "04_functions.sql"
            p.write_bytes(
                p.read_bytes().replace(b"RAISE EXCEPTION", b"RAISE NOTICE", 1)
            )
            with self.assertRaisesRegex(RuntimeError, "CHECKSUM_MISMATCH"):
                load_baseline(dest)

    def test_missing_fk_target_rejected(self):
        broken = [
            s
            for s in self.statements
            if not (
                isinstance(parse_sql(s)[0].stmt, ast.IndexStmt)
                and parse_sql(s)[0].stmt.idxname == "uq_model_versions_id_training_run"
            )
        ]
        self.assertLess(len(broken), len(self.statements))
        with self.assertRaisesRegex(AssertionError, "FK target not unique"):
            catalogue(broken)

    def test_trigger_with_missing_function_rejected(self):
        broken = [
            s
            for s in self.statements
            if not s.startswith("CREATE OR REPLACE FUNCTION public.train_event_guard(")
        ]
        self.assertLess(len(broken), len(self.statements))
        with self.assertRaises(AssertionError):
            catalogue(broken)

    def test_scientific_types_and_nullable_auc(self):
        cols = self.catalogue["tables"]["run_clinical_metrics"]
        for name in ("tp", "fp", "fn", "tn"):
            self.assertEqual(cols[name].typeName.names[-1].sval, "int8")
            self.assertTrue(
                any(
                    c.contype == ConstrType.CONSTR_NOTNULL
                    for c in cols[name].constraints
                )
            )
        for name in (
            "recall_parasitized",
            "specificity",
            "roc_auc_parasitized",
            "pr_auc_parasitized",
        ):
            self.assertIsNone(cols[name].typeName.typmods)
            self.assertFalse(
                any(
                    c.contype == ConstrType.CONSTR_NOTNULL
                    for c in cols[name].constraints or ()
                )
            )
        epoch = self.catalogue["constraints"][("training_history", "uq_v2_epoch")]
        self.assertEqual([c.sval for c in epoch.keys], ["run_id", "phase", "epoch"])

    def test_single_technical_seed_and_no_transaction_escape(self):
        inserts = [
            s
            for s in self.statements
            if isinstance(parse_sql(s)[0].stmt, ast.InsertStmt)
        ]
        self.assertEqual(len(inserts), 1)
        seed = parse_sql(inserts[0])[0].stmt
        self.assertEqual(seed.relation.relname, "experiment_execution_gate")
        self.assertEqual(len(seed.selectStmt.valuesLists), 1)
        self.assertEqual(len(seed.selectStmt.valuesLists[0]), 5)
        for sql in self.statements:
            self.assertNotRegex(
                sql, r"(?i)CREATE\s+INDEX\s+CONCURRENTLY|^COMMIT|^TRUNCATE|^DROP "
            )
        self.assertNotIn("alembic_version", self.catalogue["tables"])

    def test_calibration_cycle_preserves_deferred_foreign_keys(self):
        found = []
        for (table, _), constraint in self.catalogue["constraints"].items():
            if (
                table == "run_threshold_calibration"
                and constraint.contype == ConstrType.CONSTR_FOREIGN
            ):
                columns = [c.sval for c in constraint.fk_attrs]
                if columns in (["default_evaluation_id"], ["selected_evaluation_id"]):
                    found.append(columns)
                    self.assertTrue(constraint.deferrable)
                    self.assertTrue(constraint.initdeferred)
                    self.assertEqual(constraint.pktable.relname, "evaluations")
        self.assertEqual(len(found), 2)


class ExternalAmendmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = catalogue(load_baseline()[1])
        cls.constraints = cls.catalogue["constraints"]

    def check(self, name, row):
        return expression(self.constraints[("evaluations", name)].raw_expr, row)

    def test_scope_truth_table_keeps_official_splits(self):
        for split, purpose, role in (
            ("train", "development", "development"),
            ("val", "development", "training_validation_final"),
            ("test", "final", "final_test"),
            ("external", "complementary", "external_complementary"),
        ):
            with self.subTest(split=split):
                self.assertIs(
                    self.check(
                        "ck_v2_evaluation_scope",
                        {"split": split, "purpose": purpose, "evaluation_role": role},
                    ),
                    True,
                )

    def test_external_cannot_be_validation_test_or_calibration(self):
        for purpose in ("development", "final", "complementary"):
            for role in (
                "development",
                "training_validation_final",
                "final_test",
                "calibration_default",
                "calibration_selected",
            ):
                with self.subTest(purpose=purpose, role=role):
                    self.assertIs(
                        self.check(
                            "ck_v2_evaluation_scope",
                            {
                                "split": "external",
                                "purpose": purpose,
                                "evaluation_role": role,
                            },
                        ),
                        False,
                    )

    def test_external_validation_is_not_an_evaluation_alias(self):
        for split in ("external_validation", "validation", "unknown"):
            self.assertIs(
                self.check(
                    "ck_v2_evaluation_scope",
                    {
                        "split": split,
                        "purpose": "complementary",
                        "evaluation_role": "external_complementary",
                    },
                ),
                False,
            )
        protected = self.constraints[
            ("dataset_split_assignments", "chk_dataset_split_assignments_split")
        ]
        self.assertIs(
            expression(protected.raw_expr, {"split_name": "external_validation"}), True
        )
        self.assertIs(expression(protected.raw_expr, {"split_name": "external"}), False)

    def test_external_requires_actual_population_and_provenance_fields(self):
        row = {
            "split": "external",
            "dataset_origin_id": "synthetic-id",
            "dataset_origin_role": "explicit-source-role",
            "population_manifest_uri": "fixture://population",
            "population_manifest_sha256": "a" * 64,
            "dataset_provenance_uri": "fixture://provenance",
            "dataset_provenance_sha256": "b" * 64,
            "source_kind": "external_record",
            "source_record_key": "synthetic-1",
            "source_record_phase": "external-v1",
        }
        self.assertIs(self.check("ck_v2_external_provenance", row), True)
        for field in (
            "dataset_origin_id",
            "dataset_origin_role",
            "population_manifest_uri",
            "population_manifest_sha256",
            "dataset_provenance_uri",
            "dataset_provenance_sha256",
        ):
            with self.subTest(field=field):
                self.assertIs(
                    self.check("ck_v2_external_provenance", dict(row, **{field: None})),
                    False,
                )
        for field in (
            "population_manifest_uri",
            "dataset_provenance_uri",
            "source_record_key",
            "source_record_phase",
        ):
            self.assertIs(
                self.check("ck_v2_external_provenance", dict(row, **{field: "  "})),
                False,
            )
        for kind in ("e10", "assessment"):
            self.assertIs(
                self.check("ck_v2_external_provenance", dict(row, source_kind=kind)),
                False,
            )
        self.assertIs(
            self.check("ck_v2_external_provenance", dict(row, source_kind="legacy")),
            True,
        )
        self.assertIs(
            self.check(
                "ck_v2_external_provenance",
                dict(row, dataset_provenance_sha256="not-a-hash"),
            ),
            False,
        )

    def test_provenance_fk_targets_existing_protected_key(self):
        fk = self.constraints[("evaluations", "fk_v2_evaluation_dataset_origin")]
        self.assertEqual(fk.pktable.relname, "dataset_version_sources")
        self.assertEqual(
            [c.sval for c in fk.pk_attrs], ["dataset_version_id", "dataset_id", "role"]
        )

    def test_official_and_complementary_views_are_separate(self):
        views = self.catalogue["views"]
        for split in ("train", "val", "test", "external"):
            self.assertEqual(
                expression(
                    views["vw_v2_model_comparison"].query.whereClause, {"split": split}
                ),
                split != "external",
            )
            self.assertEqual(
                expression(
                    views["vw_v2_external_evidence"].query.whereClause, {"split": split}
                ),
                split == "external",
            )
        columns = {
            t.name for t in views["vw_v2_external_evidence"].query.targetList if t.name
        }
        raw_fields = {
            t.val.fields[-1].sval
            for t in views["vw_v2_external_evidence"].query.targetList
            if isinstance(t.val, ast.ColumnRef)
        }
        self.assertTrue(
            {
                "population_hash",
                "protocol_hash",
                "dataset_origin_id",
                "dataset_provenance_uri",
            }
            <= raw_fields | columns
        )

    def test_metric_projection_preserves_external_and_calibration_requires_val(self):
        funcs = self.catalogue["functions"]
        body = lambda name: next(
            o.arg[0].sval for o in funcs["public." + name].options if o.defname == "as"
        )
        self.assertIn("NEW.split_name:=e.split", body("v2_binary_metric_guard"))
        self.assertIn(
            "d.split<>'val' OR s.split<>'val'", body("v2_calibration_pair_guard")
        )
        self.assertIn(
            "e.split<>'external' AND r.dataset_version_id IS DISTINCT FROM e.dataset_version_id",
            body("v2_evaluation_complete"),
        )
        self.assertIn("calibration_split='val'", body("v2_evaluation_complete"))


def target_fixture():
    return {
        "authorized_stage": "E10.10.5B",
        "gate_a_approved": True,
        "isolation_id": "b7994a3d-b7f7-4c87-91c4-64f001738a57",
        "database": "capstone_v2_isolated_fixture",
        "container_id": "a" * 64,
        "volume": "capstone_v2_isolated_fixture",
        "postgres_system_identifier": "123456789",
        "database_oid": 123,
        "host_port": 55439,
    }


class SafetyTests(unittest.TestCase):
    def test_b01_roles_are_nonreserved_and_executable_references_are_consistent(self):
        from alembic_v2.safety import MIGRATOR, RUNTIME

        self.assertEqual(MIGRATOR, "capstone_v2_migrator")
        self.assertEqual(RUNTIME, "capstone_v2_runtime")
        root = BASELINE.parents[1]
        paths = list((root / "alembic_v2").rglob("*.py"))
        paths += list(BASELINE.glob("*.sql"))
        paths += [
            root / "scripts/db" / name
            for name in (
                "build_v2_baseline.py",
                "certify_v2_route_a.py",
                "verify_v2_route_a.py",
                "v2_catalog_probe.py",
                "test_v2_route_a_server.py",
            )
        ]
        for path in paths:
            self.assertNotRegex(
                path.read_text(), r"\bpg_" + r"v2_(migrator|runtime)\b", str(path)
            )

    def setUp(self):
        self.target = target_fixture()
        self.identity = {
            "database": self.target["database"],
            "database_oid": 123,
            "system_identifier": "123456789",
            "role": "capstone_v2_migrator",
            "session_role": "capstone_v2_migrator",
            "database_owner": "capstone_v2_migrator",
            "server_version_num": 170006,
            "data_directory": "/var/lib/postgresql/data",
            "recovery": False,
            "read_only": "off",
        }
        flags = {
            "rolsuper": False,
            "rolcreatedb": False,
            "rolcreaterole": False,
            "rolreplication": False,
            "rolbypassrls": False,
            "has_membership": False,
        }
        self.roles = [
            dict(flags, rolname="capstone_v2_migrator"),
            dict(flags, rolname="capstone_v2_runtime"),
        ]
        self.url = "postgresql+psycopg://capstone_v2_migrator@127.0.0.1:55439/capstone_v2_isolated_fixture"

    def test_explicit_authorization_required(self):
        with self.assertRaises(UnsafeTarget):
            read_authorization(None, self.url)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(self.target))
            self.assertEqual(read_authorization(path, self.url), self.target)
            for url in (
                self.url.replace("55439", "5432"),
                self.url + "?host=production",
                self.url.replace("127.0.0.1", "localhost"),
                self.url.replace("capstone_v2_migrator", "postgres"),
            ):
                with self.subTest(url=url), self.assertRaises(UnsafeTarget):
                    read_authorization(path, url)
            path.write_text(json.dumps(dict(self.target, gate_a_approved=False)))
            with self.assertRaises(UnsafeTarget):
                read_authorization(path, self.url)

    def test_cluster_database_version_and_owner_must_all_match(self):
        validate_server_snapshot(self.target, self.identity, self.roles)
        for field, value in [
            ("system_identifier", "999"),
            ("database_oid", 999),
            ("role", "postgres"),
            ("server_version_num", 180000),
            ("database_owner", "postgres"),
            ("recovery", True),
        ]:
            with self.subTest(field=field), self.assertRaises(UnsafeTarget):
                validate_server_snapshot(
                    self.target, dict(self.identity, **{field: value}), self.roles
                )

    def test_dbv22_requires_exact_17_9_and_approved_contract(self):
        target = dict(self.target, authorized_stage="DBV2.2", gate_dbv21_approved=True)
        validate_server_snapshot(target, dict(self.identity, server_version_num=170009), self.roles)
        for version in (170008, 170010, 180000):
            with self.subTest(version=version), self.assertRaises(UnsafeTarget):
                validate_server_snapshot(target, dict(self.identity, server_version_num=version), self.roles)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "target.json"
            path.write_text(json.dumps(target))
            self.assertEqual(read_authorization(path, self.url), target)
            path.write_text(json.dumps(dict(target, gate_dbv21_approved=False)))
            with self.assertRaises(UnsafeTarget):
                read_authorization(path, self.url)

    def test_privileged_or_inherited_runtime_role_rejected(self):
        for flag in (
            "rolsuper",
            "rolcreatedb",
            "rolcreaterole",
            "rolbypassrls",
            "rolreplication",
            "has_membership",
        ):
            roles = copy.deepcopy(self.roles)
            roles[1][flag] = True
            with self.subTest(flag=flag), self.assertRaises(UnsafeTarget):
                validate_server_snapshot(self.target, self.identity, roles)

    def test_volume_mount_and_container_identity_not_just_database_name(self):
        mount = {
            "Type": "volume",
            "Name": self.target["volume"],
            "Destination": "/var/lib/postgresql/data",
            "RW": True,
            "Source": "/isolated/fixture",
        }
        container = {
            "Id": self.target["container_id"],
            "State": {"Running": True},
            "Config": {
                "Labels": {LABEL: self.target["isolation_id"]},
                "Env": ["PGDATA=/var/lib/postgresql/data"],
            },
            "HostConfig": {"Privileged": False, "NetworkMode": "isolated"},
            "Mounts": [mount],
            "NetworkSettings": {
                "Ports": {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "55439"}]}
            },
        }
        volume = {
            "Name": self.target["volume"],
            "Driver": "local",
            "Scope": "local",
            "Options": None,
            "Labels": {LABEL: self.target["isolation_id"]},
            "Mountpoint": mount["Source"],
        }
        validate_docker_snapshot(self.target, container, volume, [container])
        other = {"Id": "b" * 64, "Mounts": [mount]}
        with self.assertRaisesRegex(UnsafeTarget, "SHARED_WITH_ANOTHER"):
            validate_docker_snapshot(self.target, container, volume, [container, other])
        broken = copy.deepcopy(container)
        broken["Mounts"][0]["Type"] = "bind"
        with self.assertRaises(UnsafeTarget):
            validate_docker_snapshot(self.target, broken, volume, [broken])
        broken = copy.deepcopy(container)
        broken["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostIp"] = "0.0.0.0"
        with self.assertRaises(UnsafeTarget):
            validate_docker_snapshot(self.target, broken, volume, [broken])


if __name__ == "__main__":
    unittest.main()
