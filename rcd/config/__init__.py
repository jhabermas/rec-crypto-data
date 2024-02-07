import os

from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="RCD",
    settings_files=["settings.toml", ".secrets.toml"],
)

mappings = Dynaconf(
    envvar_prefix="RCD_MAPPINGS",
    settings_files=["mappings.toml"],
)


def get_module_config(module_name):
    module = module_name.split(".")
    config_path = os.path.join(*module)
    config = Dynaconf(
        envvar_prefix=f"RCD_{module_name}",
        settings_files=[f"{module_name}.toml"],
    )
    return config
