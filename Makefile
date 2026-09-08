PYTHON := .venv/bin/python
PYTHONPATH := src

.PHONY: setup load test api ui check-consistency load-internal

setup:            ## Create venv and install dependencies
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

load:             ## Parse ontology files and print a dataset summary
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m banking_kb.kb

load-internal:    ## Parse ontology files plus internal/*.ttl (git-ignored data)
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m banking_kb.kb internal

test:             ## Run the pytest suite (maps to the OpenSpec spec scenarios)
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest tests -q

api:              ## Start the FastAPI demo server on http://127.0.0.1:8000
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m uvicorn banking_kb.api:app --reload --host 127.0.0.1 --port 8000

ui:               ## Start the Streamlit demo UI on http://127.0.0.1:8501
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m streamlit run ui/app.py

check-consistency:## Optional HermiT satisfiability gate (requires Java)
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m banking_kb.consistency
