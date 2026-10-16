from __future__ import annotations

import os
from collections.abc import Mapping


def local_services_enabled(
    environment: Mapping[str, str] | None = None,
) -> bool:
    """Enable disk storage and Ollama only when explicitly opted into."""
    values = os.environ if environment is None else environment
    return values.get("CROPSHIELD_LOCAL_MODE", "").strip().casefold() in {
        "1",
        "true",
        "yes",
    }
