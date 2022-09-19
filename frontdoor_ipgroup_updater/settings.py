from pathlib import Path
from typing import Any

import tomli
from pydantic import UUID4, BaseSettings
from pydantic.env_settings import SettingsSourceCallable


def toml_settings_source(_: BaseSettings) -> dict[str, Any]:
    config_path = Path("config.toml")

    if not config_path.exists() or not config_path.is_file():
        return {}

    with config_path.open("rb") as config_file:
        return tomli.load(config_file)


class Settings(BaseSettings):
    class Config:
        secrets_dir = "/var/run/secrets/frontdoor-ipgroup-updater"

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> tuple[SettingsSourceCallable, ...]:
            """Include a TOML settings source."""
            return (
                init_settings,
                toml_settings_source,
                env_settings,
                file_secret_settings,
            )

    application_id: UUID4
    application_secret: str
    tenant_id: UUID4
    subscription_id: UUID4
    resource_group_name: str
    ip_group_name: str
    minimum_acceptable_v4_networks: int = 60


settings = Settings()
