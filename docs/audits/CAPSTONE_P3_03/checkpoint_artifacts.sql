BEGIN READ ONLY;
SELECT json_agg(to_jsonb(a)) FROM artifacts a WHERE id IN ('67a4c360-265b-5565-ab2f-8a72c11d60bc','64fe7053-bb87-5e65-ab9a-0637ec4f9a4f');
COMMIT;
