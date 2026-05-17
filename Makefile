.PHONY: bootstrap install seed slice approve curate-memory brief test clean llama-chat llama-embed healthz \
        telegram-bridge wa-bridge wuzapi dashboard tunnel worker worker-once \
        start-task compile-prd approve-prd autoloop \
        search-monitor compose-up compose-down compose-logs compose-build

PY=.venv/bin/python
PIP=.venv/bin/pip

bootstrap:
	test -d .venv || python3 -m venv .venv
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -e ".[dev]"
	@echo "venv ready. activate with: source .venv/bin/activate"

install: bootstrap

seed:
	$(PY) -m seed.seed_acme

slice: seed
	$(PY) -m consilo.cli run-slice

approve:
	$(PY) -m consilo.cli approve OC-T-001 --apply

curate-memory:
	$(PY) -m consilo.cli curate-memory --client acme

brief:
	$(PY) -m consilo.cli brief --client acme --project digital-platform

search-monitor:
	$(PY) -m consilo.cli search-monitor --all

start-task:
	$(PY) -m consilo.cli start-task --client $${CLIENT:-acme} --project $${PROJECT:-new-task}

compile-prd:
	$(PY) -m consilo.cli compile-prd --client $${CLIENT:-acme} --project $${PROJECT:-new-task}

approve-prd:
	$(PY) -m consilo.cli approve-prd --client $${CLIENT:-acme} --project $${PROJECT:-new-task} --autoloop

autoloop:
	$(PY) -m consilo.cli autoloop --client $${CLIENT:-acme} --project $${PROJECT:-new-task}

worker:
	$(PY) -m consilo.cli worker --interval $${INTERVAL:-300}

worker-once:
	$(PY) -m consilo.cli worker --once

compose-up:
	docker compose up -d

compose-down:
	docker compose down

compose-logs:
	docker compose logs -f --tail=200

compose-build:
	docker compose build consilo-bridge consilo-dashboard

test:
	$(PY) -m pytest

clean:
	rm -rf data/ tasks/ .pytest_cache/
	find vault/clients -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +

llama-chat:
	bash scripts/llama_chat_server.sh

llama-embed:
	bash scripts/llama_embed_server.sh

healthz:
	bash scripts/healthz.sh

telegram-bridge:
	bash scripts/telegram_bridge.sh

wa-bridge:
	bash scripts/wa_bridge.sh

wuzapi:
	bash scripts/wuzapi.sh

dashboard:
	bash scripts/dashboard.sh

tunnel:
	bash scripts/cloudflared_setup.sh
