.PHONY: help install install-viewer build-viewer build test test-e2e audit audit-python audit-viewer update-deps update-python update-viewer samples samples-pdf clean all

help:
	@echo "md-style v3 Build System"
	@echo "  make install         - Install Python dependencies via uv"
	@echo "  make install-viewer  - Install Svelte viewer npm dependencies"
	@echo "  make build-viewer    - Recompile Svelte 5 interactive viewer bundle (with Mermaid)"
	@echo "  make build           - Build viewer assets and Python environment"
	@echo "  make test            - Run pytest suite"
	@echo "  make test-e2e        - Run Playwright E2E headless browser test suite"
	@echo "  make audit           - Security vulnerability audit for Python (pip-audit) and viewer (npm audit)"
	@echo "  make update-deps     - Upgrade dependencies and lockfiles for both Python (uv) and viewer (npm)"
	@echo "  make samples         - Compile all example reports to output/ (HTML)"
	@echo "  make samples-pdf     - Compile sample reports to output/ (PDF via Chromium)"
	@echo "  make clean           - Clean output, cache, and transient build artifacts"
	@echo "  make all             - Full end-to-end setup, build, test, and render"

install:
	uv sync

install-viewer:
	cd viewer && npm install

build-viewer:
	cd viewer && npm run build

build: build-viewer

test:
	uv run pytest -v

test-e2e:
	uv run pytest tests/e2e/ -v

audit-python:
	@echo "==> Auditing Python dependencies (pip-audit via uvx)..."
	uvx pip-audit

audit-viewer:
	@echo "==> Auditing Viewer npm dependencies..."
	cd viewer && npm audit

audit: audit-python audit-viewer

update-python:
	@echo "==> Upgrading Python dependencies and updating uv.lock..."
	uv lock --upgrade
	uv sync

update-viewer:
	@echo "==> Upgrading Viewer npm packages and rebuilding bundle..."
	cd viewer && npm update
	cd viewer && npm run build

update-deps: update-python update-viewer
	@echo "==> All Python and TypeScript/Viewer dependencies updated successfully."


samples:
	@mkdir -p output
	uv run md-style examples/sample-forensic-cyber.md -s forensic/cyber -o output/sample-forensic-cyber.html
	uv run md-style examples/sample-forensic-report.md -s forensic/dossier -o output/sample-forensic-report.html
	uv run md-style "examples/pozvánka-shromáždění-svj.md" -s svj/invitation -o output/pozvanka-svj.html
	uv run md-style examples/announcement-sample.md -s general/announcement -o output/announcement.html
	uv run md-style examples/school-report-sample.md -s general/school -o output/school-report.html
	uv run md-style examples/family-invite-sample.md -s general/family-invite -o output/family-invite.html

samples-pdf: samples
	uv run md-style examples/sample-forensic-cyber.md -s forensic/cyber -p -o output/sample-forensic-cyber.pdf
	uv run md-style examples/sample-forensic-report.md -s forensic/dossier -p -o output/sample-forensic-report.pdf
	uv run md-style "examples/pozvánka-shromáždění-svj.md" -s svj/invitation -p -o output/pozvanka-svj.pdf
	uv run md-style examples/school-report-sample.md -s general/school -p -o output/school-report.pdf

clean:
	rm -rf output/ .pytest_cache/ viewer/dist/
	find . -type d -name "__pycache__" -exec rm -rf {} +
