"""JSON file-based storage for user-defined API configurations."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models.api_config import ApiEndpointConfig

logger = logging.getLogger(__name__)


class ConfigStorage:
    """Manages user-defined API configs as individual JSON files."""

    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, config_id: str) -> Path:
        return self.config_dir / f"{config_id}.json"

    def list_configs(self) -> list[dict[str, Any]]:
        """Return all user-defined configs with metadata."""
        configs = []
        for json_file in sorted(self.config_dir.glob("*.json")):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                configs.append(data)
            except Exception:
                logger.exception(f"Failed to load config from {json_file}")
        return configs

    def get_config(self, config_id: str) -> dict[str, Any] | None:
        """Get a single config by ID."""
        path = self._file_path(config_id)
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def save_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """Save a new user config. Assigns an ID and timestamps."""
        config_id = str(uuid.uuid4())
        config_data["id"] = config_id
        config_data["source"] = "user"
        config_data["created_at"] = datetime.now(UTC).isoformat()
        config_data["updated_at"] = config_data["created_at"]

        # Validate that the core fields produce a valid ApiEndpointConfig
        self._validate_endpoint(config_data)

        with open(self._file_path(config_id), "w") as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"Saved user config: {config_data.get('name')} ({config_id})")
        return config_data

    def update_config(self, config_id: str, config_data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an existing user config."""
        path = self._file_path(config_id)
        if not path.exists():
            return None

        # Preserve original metadata
        with open(path) as f:
            existing = json.load(f)

        config_data["id"] = config_id
        config_data["source"] = "user"
        config_data["created_at"] = existing.get("created_at", datetime.now(UTC).isoformat())
        config_data["updated_at"] = datetime.now(UTC).isoformat()

        self._validate_endpoint(config_data)

        with open(path, "w") as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"Updated user config: {config_data.get('name')} ({config_id})")
        return config_data

    def delete_config(self, config_id: str) -> bool:
        """Delete a user config. Returns True if deleted."""
        path = self._file_path(config_id)
        if not path.exists():
            return False
        path.unlink()
        logger.info(f"Deleted user config: {config_id}")
        return True

    @staticmethod
    def _validate_endpoint(data: dict[str, Any]) -> None:
        """Validate that the data can produce a valid ApiEndpointConfig."""
        # Extract only the fields that ApiEndpointConfig expects
        endpoint_fields = {k: v for k, v in data.items() if k in ApiEndpointConfig.model_fields}
        ApiEndpointConfig(**endpoint_fields)
