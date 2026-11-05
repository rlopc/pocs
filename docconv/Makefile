.PHONY: update-tooling

# Update uv itself (installed with Homebrew), then install the exact Python patch
# pinned in .python-version (e.g. 3.14.7).
update-tooling:
	brew update
	brew upgrade uv
	uv python install "$$(cat .python-version)"

.PHONY: check-versions

# Check that versions are in sync. The Dockerfile is the reference: Dependabot
# keeps it up to date. Prints how to fix each mismatch. Changes nothing.
# - uv: the workflow pins the same version as the Dockerfile, and the local uv
#   (Homebrew, always the latest) is not older than it. A newer one is fine.
# - Python: .python-version pins the same patch as the Dockerfile, and that patch
#   is installed locally.
check-versions:
	@docker_v=$$(sed -n 's|^FROM ghcr.io/astral-sh/uv:\([0-9.]*\).*|\1|p' Dockerfile); \
	ci_v=$$(sed -n 's|^  UV_VERSION: "\([0-9.]*\)"|\1|p' ../.github/workflows/docconv.yml); \
	local_v=$$(uv --version | cut -d' ' -f2); \
	py_docker=$$(sed -n 's|^FROM python:\([0-9.]*\).*|\1|p' Dockerfile); \
	py_pin=$$(cat .python-version); \
	py_path=$$(uv python find 2>/dev/null); \
	py_local=; \
	if [ -n "$$py_path" ]; then \
		py_local=$$("$$py_path" -c 'import platform; print(platform.python_version())'); \
	fi; \
	if [ -z "$$docker_v" ] || [ -z "$$py_docker" ]; then \
		echo "Could not read the uv or Python version from the Dockerfile FROM lines"; \
		exit 1; \
	fi; \
	status=0; \
	if [ "$$ci_v" != "$$docker_v" ]; then \
		echo "Workflow: set UV_VERSION to \"$$docker_v\" in .github/workflows/docconv.yml (now: \"$$ci_v\")"; \
		status=1; \
	fi; \
	oldest=$$(printf '%s\n%s\n' "$$docker_v" "$$local_v" | sort -V | head -n 1); \
	if [ "$$oldest" != "$$docker_v" ]; then \
		echo "Local uv: run 'make update-tooling' or 'brew update && brew upgrade uv' (now: $$local_v, need >= $$docker_v)"; \
		status=1; \
	fi; \
	if [ "$$py_pin" != "$$py_docker" ]; then \
		echo "Python: set .python-version to $$py_docker (now: $$py_pin)"; \
		status=1; \
	fi; \
	if [ "$$py_local" != "$$py_pin" ]; then \
		echo "Local Python: run 'make update-tooling' or 'uv python install $$py_pin' (now: $${py_local:-not installed})"; \
		status=1; \
	fi; \
	if [ "$$status" -eq 0 ]; then \
		echo "OK: uv $$docker_v (local $$local_v), Python $$py_docker"; \
	fi; \
	exit $$status
