import os, subprocess
from dotenv import dotenv_values
from sqlalchemy import URL
config=dotenv_values('.env')
env=dict(os.environ, CAPSTONE_LOCAL_TRAIN='1', RUN_STAGE4_POSTGRES_TESTS='1', PYTHONPATH='malaria_dl_local_project')
env['DATABASE_URL']=URL.create('postgresql+psycopg',username=config['POSTGRES_USER'],password=config['POSTGRES_PASSWORD'],host='127.0.0.1',port=5432,database=config['POSTGRES_DB']).render_as_string(hide_password=False)
files=['test_model_execution_tracking.py','test_max_epochs_tracking.py','test_prepare_model_release_service.py','test_campaigns_postgres.py','test_train_run_persistence.py','test_runtime_environment_contract.py']
with open('docs/audits/model_contract_01a/tests.txt','w') as out:
 result=subprocess.run(['malaria_dl_local_project/.venv-local-train/bin/python','-m','pytest',*[f'malaria_dl_local_project/tests/{f}' for f in files],'-q'],env=env,stdout=out,stderr=subprocess.STDOUT)
print('pytest exit:',result.returncode)
