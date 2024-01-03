from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="RCD",
    settings_files=["settings.toml", ".secrets.toml"],
)

mappings = Dynaconf(
    envvar_prefix="RCD_MAPPINGS",
    settings_files=["mappings.toml"],
)
