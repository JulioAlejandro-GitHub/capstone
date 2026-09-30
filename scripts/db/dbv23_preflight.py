"""Only aggregate source READ ONLY checks; never image files or credential values."""

from dbv23_source import OFFICIAL, read, save


def main():
    checks = {
        "official_version": f"SELECT coalesce(json_agg(q),'[]'::json) FROM (SELECT id,status,source_record_count,frozen_at IS NOT NULL AS frozen_at_present FROM dataset_versions WHERE id='{OFFICIAL}') q",
        "splits": f"SELECT json_agg(q) FROM (SELECT split_name,count(*) AS images,count(DISTINCT clinical_identity_id) AS patients FROM dataset_split_assignments WHERE dataset_version_id='{OFFICIAL}' GROUP BY split_name ORDER BY split_name) q",
        "official_total": f"SELECT json_build_object('total',count(*),'patients',count(DISTINCT clinical_identity_id)) FROM dataset_split_assignments WHERE dataset_version_id='{OFFICIAL}'",
        "physical_roots": "SELECT json_agg(q) FROM (SELECT dataset_dir,dataset_version_id,count(*) AS records FROM dataset_split_images GROUP BY dataset_dir,dataset_version_id ORDER BY dataset_dir,dataset_version_id) q",
        "assignment_source_mismatches": f"SELECT count(*) FROM dataset_split_assignments a LEFT JOIN dataset_source_records s ON s.id=a.source_record_id WHERE a.dataset_version_id='{OFFICIAL}' AND (s.id IS NULL OR a.clinical_identity_id IS DISTINCT FROM s.clinical_identity_id OR a.class_index IS DISTINCT FROM s.class_index OR a.class_name IS DISTINCT FROM s.class_name)",
        "patients_in_multiple_splits": f"SELECT count(*) FROM (SELECT clinical_identity_id FROM dataset_split_assignments WHERE dataset_version_id='{OFFICIAL}' GROUP BY clinical_identity_id HAVING count(DISTINCT split_name)>1) q",
        "activation_version_mismatches": "SELECT count(*) FROM dataset_materialization_activations a LEFT JOIN dataset_materializations m ON m.id=a.materialization_id WHERE a.dataset_version_id IS DISTINCT FROM m.dataset_version_id",
        "user_status_counts": "SELECT coalesce(json_agg(q),'[]'::json) FROM (SELECT status,count(*) AS users FROM users GROUP BY status ORDER BY status) q",
        "users_with_roles": "SELECT count(*) FROM users u WHERE EXISTS (SELECT 1 FROM user_roles r WHERE r.user_id=u.id)",
        "referenced_role_count": "SELECT count(DISTINCT role_id) FROM user_roles",
    }
    data = {k: read(q) for k, q in checks.items()}
    save("data_preflight.json", data)
    assert data["official_total"] == {"total": 27558, "patients": 201}
    splits = {r["split_name"]: r["images"] for r in data["splits"]}
    assert splits == {"TRAIN": 22180, "VAL": 2693, "TEST": 2685} or splits == {
        "train": 22180,
        "val": 2693,
        "test": 2685,
    }, splits
    assert all(
        data[k] == 0
        for k in (
            "assignment_source_mismatches",
            "patients_in_multiple_splits",
            "activation_version_mismatches",
        )
    )
    assert len(data["physical_roots"]) == 2 and all(
        r["records"] == 27558 for r in data["physical_roots"]
    )
    assert (
        len(data["official_version"]) == 1
        and data["official_version"][0]["frozen_at_present"]
    )
    print(
        "PASS source aggregate data preflight; no row transfer or password hash reads."
    )


if __name__ == "__main__":
    main()
