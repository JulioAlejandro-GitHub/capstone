AUDIT_PYTHON ?= malaria_dl_local_project/.venv-local-train/bin/python
.PHONY: test
test:
	PYTHONDONTWRITEBYTECODE=1 $(AUDIT_PYTHON) -m unittest discover -s scripts/audit_s1_1 -p 'test_audit.py' -v
