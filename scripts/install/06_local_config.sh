#!/usr/bin/env bash

stage_local_config() {
  say "Stage 6/6: prepare local config files"

  if [[ ! -f "$REPO_ROOT/config/config.yaml" ]]; then
    CONFIG_CREATED=1
    cp "$REPO_ROOT/config/config.example.yaml" "$REPO_ROOT/config/config.yaml"
    echo "[install] Created $REPO_ROOT/config/config.yaml from the example template. Edit your real keywords here."
  fi

  if [[ ! -f "$REPO_ROOT/.env" ]]; then
    ENV_CREATED=1
    cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
    echo "[install] Created $REPO_ROOT/.env. Edit SMTP and recipient settings before first run."
  fi
}
