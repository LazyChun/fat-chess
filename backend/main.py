"""
FatNotes Bespoke Plugin — Backend Entry Point

This is the main entry file for your plugin's backend process.
Register handlers using the @handler decorator. Each handler receives
a params dict and should return a JSON-serializable result.

The frontend calls handlers via:
    const result = await sdk.backend.invoke("handlerName", { key: "value" });

IMPORTANT: Only write backend code for functionality that the SDK cannot provide.
Prefer sdk.query, sdk.mutation, sdk.dataSource for data operations.
Use backend handlers for: file processing, external API calls, heavy computation,
or when you need Python libraries not available in the host.
"""

from plugin_runtime import (
    handler,
    run,
    host_get_plugin_config,
    host_set_plugin_config,
    host_get_system_paths,
)


@handler("hello")
def hello(params):
    """Example handler — replace with your own logic."""
    name = params.get("name", "World")
    return {"message": f"Hello from fat-chess backend, {name}!"}


@handler("echo")
def echo(params):
    """Echo back the received params — useful for testing."""
    return {"received": params}


@handler("getSystemPaths")
def get_system_paths(_params):
    """Read system paths from host."""
    return host_get_system_paths()


@handler("getPluginConfig")
def get_plugin_config(_params):
    """Read this plugin's runtime config from host."""
    return host_get_plugin_config()


@handler("setPluginConfig")
def set_plugin_config(params):
    """Update this plugin's runtime config in host."""
    config_data = params.get("config", {}) if isinstance(params, dict) else {}
    merge = True
    if isinstance(params, dict):
        merge = bool(params.get("merge", True))
    return host_set_plugin_config(config_data, merge=merge)


if __name__ == "__main__":
    run()
