"""Read PostgreSQL catalog properties without database-local OIDs in comparisons."""

QUERIES = {
    "default_functions": """SELECT c.relname AS relation,a.attname AS column_name,
        n.nspname AS function_schema,p.proname AS function_name,
        pg_get_function_identity_arguments(p.oid) AS arguments,
        pg_get_function_result(p.oid) AS result
        FROM pg_attrdef d JOIN pg_class c ON c.oid=d.adrelid
        JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=d.adnum
        CROSS JOIN LATERAL regexp_matches(d.adbin::text, ':funcid ([0-9]+)', 'g') f(id)
        JOIN pg_proc p ON p.oid=f.id[1]::oid JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE c.relnamespace='public'::regnamespace ORDER BY 1,2,3,4,5""",
    "default_dependencies": """SELECT c.relname AS relation,a.attname AS column_name,
        x.deptype,x.refclassid::regclass::text AS referenced_catalog,
        pg_describe_object(x.refclassid,x.refobjid,x.refobjsubid) AS referenced_object
        FROM pg_attrdef d JOIN pg_class c ON c.oid=d.adrelid
        JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=d.adnum
        JOIN pg_depend x ON x.classid='pg_attrdef'::regclass AND x.objid=d.oid
        WHERE c.relnamespace='public'::regnamespace ORDER BY 1,2,3,4,5""",
    "relations": """SELECT c.relname AS name,c.relkind,c.relpersistence,
        pg_get_userbyid(c.relowner) AS owner,c.relrowsecurity,c.relforcerowsecurity,
        c.relreplident,c.reloptions,c.relacl::text
        FROM pg_class c WHERE c.relnamespace='public'::regnamespace
        AND c.relkind IN ('r','p','v','m','S','f') ORDER BY 1""",
    "columns": """SELECT c.relname AS relation,a.attnum,a.attname AS name,
        format_type(a.atttypid,a.atttypmod) AS type,a.attnotnull,a.attidentity,a.attgenerated,
        pg_get_expr(d.adbin,d.adrelid) AS expression,
        CASE WHEN a.attcollation=0 THEN NULL ELSE a.attcollation::regcollation::text END AS collation,
        a.attacl::text
        FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
        LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
        WHERE c.relnamespace='public'::regnamespace AND a.attnum>0 AND NOT a.attisdropped
        AND c.relkind IN ('r','p','v','m','S','f') ORDER BY 1,2""",
    "constraints": """SELECT c.relname AS relation,k.conname AS name,k.contype,
        pg_get_constraintdef(k.oid,false) AS definition,k.condeferrable,k.condeferred,
        k.convalidated,k.connoinherit FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
        WHERE c.relnamespace='public'::regnamespace ORDER BY 1,2""",
    "indexes": """SELECT i.relname AS name,t.relname AS relation,pg_get_indexdef(x.indexrelid) AS definition,
        x.indisunique,x.indisprimary,x.indisvalid,x.indisready,x.indislive,x.indimmediate,
        x.indisreplident,x.indnullsnotdistinct,pg_get_userbyid(i.relowner) AS owner,
        am.amname,i.reloptions FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid
        JOIN pg_class t ON t.oid=x.indrelid JOIN pg_am am ON am.oid=i.relam
        WHERE t.relnamespace='public'::regnamespace ORDER BY 1""",
    "views": """SELECT relname AS name,pg_get_viewdef(oid,false) AS definition
        FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='v' ORDER BY 1""",
    "functions": """SELECT p.proname AS name,pg_get_function_identity_arguments(p.oid) AS arguments,
        pg_get_functiondef(p.oid) AS definition,pg_get_userbyid(p.proowner) AS owner,
        p.proacl::text,p.prosecdef,p.proleakproof,p.provolatile,p.proparallel,p.proisstrict,
        p.proconfig,e.extname AS extension
        FROM pg_proc p LEFT JOIN pg_depend d ON d.classid='pg_proc'::regclass
        AND d.objid=p.oid AND d.deptype='e' LEFT JOIN pg_extension e ON e.oid=d.refobjid
        WHERE p.pronamespace='public'::regnamespace ORDER BY 1,2""",
    "triggers": """SELECT c.relname AS relation,t.tgname AS name,
        pg_get_triggerdef(t.oid,false) AS definition,t.tgenabled,t.tgdeferrable,t.tginitdeferred
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
        WHERE c.relnamespace='public'::regnamespace AND NOT t.tgisinternal ORDER BY 1,2""",
    "sequences": """SELECT c.relname AS name,format_type(s.seqtypid,NULL) AS type,
        s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle,
        owner.relname AS owned_table,a.attname AS owned_column,d.deptype
        FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid
        LEFT JOIN pg_depend d ON d.classid='pg_class'::regclass AND d.objid=c.oid AND d.deptype IN ('a','i')
        LEFT JOIN pg_class owner ON owner.oid=d.refobjid
        LEFT JOIN pg_attribute a ON a.attrelid=d.refobjid AND a.attnum=d.refobjsubid
        WHERE c.relnamespace='public'::regnamespace ORDER BY 1""",
    "types": """SELECT t.typname AS name,t.typtype,t.typcategory,t.typnotnull,t.typdefault,
        pg_get_userbyid(t.typowner) AS owner,t.typacl::text,
        CASE WHEN t.typbasetype=0 THEN NULL ELSE format_type(t.typbasetype,t.typtypmod) END AS base_type,
        CASE WHEN t.typelem=0 THEN NULL ELSE format_type(t.typelem,NULL) END AS element_type
        FROM pg_type t WHERE t.typnamespace='public'::regnamespace ORDER BY 1""",
    "extensions": """SELECT extname AS name,extversion,pg_get_userbyid(extowner) AS owner,
        extnamespace::regnamespace::text AS schema,extrelocatable FROM pg_extension ORDER BY 1""",
    "schema_acl": """SELECT nspname,pg_get_userbyid(nspowner) AS owner,nspacl::text FROM pg_namespace
        WHERE nspname='public'""",
    "database_acl": """SELECT pg_get_userbyid(datdba) AS owner,datacl::text,
        pg_encoding_to_char(encoding) AS encoding,datcollate,datctype FROM pg_database
        WHERE datname=current_database()""",
    "default_acl": """SELECT pg_get_userbyid(defaclrole) AS role,
        defaclnamespace::regnamespace::text AS schema,defaclobjtype,defaclacl::text
        FROM pg_default_acl ORDER BY 1,2,3""",
    "roles": """SELECT rolname,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,
        rolinherit,rolcanlogin,EXISTS(SELECT 1 FROM pg_auth_members m WHERE m.member=r.oid) AS membership
        FROM pg_roles r WHERE rolname IN ('capstone_v2_migrator','capstone_v2_runtime') ORDER BY 1""",
    "runtime_privileges": """SELECT c.relname AS relation,p.privilege,
        has_table_privilege('capstone_v2_runtime',c.oid,p.privilege) AS allowed
        FROM pg_class c CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER']) p(privilege)
        WHERE c.relnamespace='public'::regnamespace AND c.relkind IN ('r','v') ORDER BY 1,2""",
    "runtime_database": """SELECT has_database_privilege('capstone_v2_runtime',current_database(),'CONNECT') AS connect,
        has_database_privilege('capstone_v2_runtime',current_database(),'CREATE') AS create,
        has_database_privilege('capstone_v2_runtime',current_database(),'TEMP') AS temp,
        has_schema_privilege('capstone_v2_runtime','public','CREATE') AS schema_create,
        has_schema_privilege('capstone_v2_runtime','public','USAGE') AS schema_usage""",
}


def snapshot(connection):
    from psycopg.rows import dict_row

    with connection.cursor(row_factory=dict_row) as c:
        c.execute("SET search_path=public,pg_catalog")
        return {name: c.execute(sql).fetchall() for name, sql in QUERIES.items()}
