from fcip_shared.config import AppSettings, get_settings

_settings = get_settings()


class BackendSettings(AppSettings):
    pass


def get_backend_settings() -> BackendSettings:
    return BackendSettings()
