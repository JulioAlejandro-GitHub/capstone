BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_agg(t) FROM (SELECT c.relname table_name,t.tgname,pg_get_triggerdef(t.oid) definition,p.proname,function_namespace.nspname function_schema FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace function_namespace ON function_namespace.oid=p.pronamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname)t;
COMMIT;
