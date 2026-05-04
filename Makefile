.PHONY: bootstrap install seed slice approve curate-memory brief test clean llama-chat llama-embed healthz \
        telegram-bridge wa-bridge wuzapi dashboard tunnel \
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
	$(PY) -m openclaw.cli run-slice

approve:
	$(PY) -m openclaw.cli approve OC-T-001 --apply

curate-memory:
	$(PY) -m openclaw.cli curate-memory --client acme

brief:
	$(PY) -m openclaw.cli brief --client acme --project digital-platform

search-monitor:
	$(PY) -m openclaw.cli search-monitor --all

compose-up:
	docker compose up -d

compose-down:
	docker compose down

compose-logs:
	docker compose logs -f --tail=200

compose-build:
	docker compose build openclaw-bridge openclaw-dashboard

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
