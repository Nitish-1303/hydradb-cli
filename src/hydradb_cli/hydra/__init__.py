"""Hand-owned wrapper around the generated ``hydradb-sdk``.

See ``CONTRACT.md`` for the canonical vocabulary and wrapper surface this
package implements.
"""

from hydradb_cli.hydra.client import HydraDB
from hydradb_cli.hydra.errors import HydraDBClientError, translate_sdk_error

__all__ = ["HydraDB", "HydraDBClientError", "translate_sdk_error"]
