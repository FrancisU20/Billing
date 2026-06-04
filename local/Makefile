.PHONY: debug-api token open-aurora close-aurora help

PYTHON := ../backend/.venv/bin/python
SCRIPTS := scripts

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

debug-api: ## 🚀 Abre Aurora + token + uvicorn (Ctrl+C cierra todo)
	$(PYTHON) $(SCRIPTS)/debug.py

token: ## 🔑 Obtén un Bearer token para Postman
	$(PYTHON) $(SCRIPTS)/auth.py

open-aurora: ## 🔓 Abre Aurora a tu IP actual (para debug con F5)
	$(PYTHON) $(SCRIPTS)/aurora.py --open

close-aurora: ## 🔒 Cierra Aurora (remueve tu IP del SG)
	$(PYTHON) $(SCRIPTS)/aurora.py --close
