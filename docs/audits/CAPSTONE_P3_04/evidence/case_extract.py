exec((__import__('pathlib').Path(__file__).parent/'extract.py').read_text().split("cols=query")[0])
t='87b3eff7-e09a-41c8-945d-bf31b3541adb'
query('principal_full_identity',"SELECT to_jsonb(i) FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id WHERE a.id='00b8d407-c672-4b68-9814-53c092d034ba';")
query('principal_scores',"SELECT json_agg(t) FROM (SELECT * FROM assessment_results WHERE attempt_id='00b8d407-c672-4b68-9814-53c092d034ba' ORDER BY sample_id)t;")
query('case_related_scores',f"SELECT json_agg(t) FROM (SELECT r.* FROM assessment_results r JOIN assessment_attempts a ON a.id=r.attempt_id JOIN assessment_identities i ON i.id=a.identity_id WHERE i.training_run_id='{t}' AND i.kind IN ('explain','represent') ORDER BY r.attempt_id,r.sample_id)t;")
query('case_identities',f"SELECT json_agg(i) FROM assessment_identities i WHERE training_run_id='{t}';")
query('secondary_identities',"SELECT json_agg(i) FROM assessment_identities i WHERE training_run_id IN ('910051e5-a00c-44c4-9d23-77598af470f7','b1b39079-658f-4300-b159-52619f981035') AND kind='represent';")
# Raw relation definitions and columns determine the joins used next.
print('case extraction complete')
