PYTHON := .venv/bin/python
PYTHONPATH := src

.PHONY: setup load test api ui check-consistency check-alignment load-internal install-skills install-skills-link

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

api:              ## Start the FastAPI server (API + web UI) on http://127.0.0.1:8000
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m uvicorn banking_kb.api:app --reload --host 127.0.0.1 --port 8000

ui:               ## Open the web UI (served by the API server)
	@echo "Web UI is served at http://127.0.0.1:8000 — starting the API server…"
	$(MAKE) api

check-consistency:## Optional HermiT satisfiability gate (requires Java)
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m banking_kb.consistency

check-alignment:  ## Verify every FIBO alignment IRI resolves in the pinned snapshot
	$(PYTHON) scripts/verify_fibo_alignment.py

install-skills:   ## Install OpenSpec skills into the user-global skill root (~/.agents/skills)
	bash scripts/install_global_skills.sh

install-skills-link: ## Same, but symlink so `openspec update` refreshes them automatically
	bash scripts/install_global_skills.sh link
