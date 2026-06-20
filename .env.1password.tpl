# 1Password-backed local development environment.
#
# Before using this template, create a 1Password item with these fields:
#   Vault: Private
#   Item: eumpa_studio local
#
# Generate .env with:
#   bash scripts/setup-env.sh

EUMPA_DATA_ROOT={{ op://Private/eumpa_studio local/EUMPA_DATA_ROOT }}
EUMPA_DATABASE_URL={{ op://Private/eumpa_studio local/EUMPA_DATABASE_URL }}
EUMPA_COMFYUI_URL={{ op://Private/eumpa_studio local/EUMPA_COMFYUI_URL }}
EUMPA_CODEX_CLI_PATH={{ op://Private/eumpa_studio local/EUMPA_CODEX_CLI_PATH }}
EUMPA_ALIGNMENT_COMMAND={{ op://Private/eumpa_studio local/EUMPA_ALIGNMENT_COMMAND }}
