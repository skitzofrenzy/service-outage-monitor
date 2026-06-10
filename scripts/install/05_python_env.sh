#!/usr/bin/env bash

stage_python_env() {
  say "Stage 5/5: create the local virtualenv and install Python dependencies"

  ensure_dir "$PROJECT_DIR"

  if [[ ! -d "$REPO_ROOT/.venv" ]]; then
    VENV_CREATED=1
    say "Creating the project virtualenv in $REPO_ROOT/.venv. This can take a few minutes."
    if command -v python >/dev/null 2>&1; then
      python -m venv "$REPO_ROOT/.venv"
    else
      python3 -m venv "$REPO_ROOT/.venv"
    fi
  else
    say "Reusing existing .venv at $REPO_ROOT/.venv"
  fi

  "$REPO_ROOT/.venv/bin/python" -m pip install --upgrade pip
  "$REPO_ROOT/.venv/bin/pip" install -r "$REPO_ROOT/requirements.txt"
}
