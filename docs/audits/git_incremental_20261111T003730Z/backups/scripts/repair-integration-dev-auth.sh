#!/usr/bin/env bash
# Compatibility entrypoint. Default inspection; --apply requires backup/restore rehearsal.
# No blanket BYPASSRLS grants, seeding, password changes or MFA exemptions.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
[[ "$ROOT" == /home/justin7m8/Documents/roadsentinel-integration ]] || {
  echo 'Refusing an unexpected workspace.' >&2; exit 1;
}
[[ -x "$ROOT/.venv.integration/bin/python" ]] || {
  echo 'The dedicated integration Python environment is required.' >&2; exit 1;
}
exec "$ROOT/.venv.integration/bin/python" "$ROOT/scripts/recover_integration_login.py" "$@"
