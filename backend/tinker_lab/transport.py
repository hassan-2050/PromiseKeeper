"""Version-scoped HTTP/2 workaround for the optional Tinker CLI only.

ServiceClient 0.35.0 has no public http_client injection hook. Its default
pyqwest path stalled on this host; standard httpx HTTP/2 reached the same API.
Keep this shim narrow, record it in config, and fail on unreviewed SDK upgrades.
"""
import importlib.metadata

import httpx


def configure_transport(config):
    if config.get("http_transport") != "httpx_http2":
        raise ValueError("Unsupported experiment HTTP transport")
    if importlib.metadata.version("tinker") != "0.35.0":
        raise ValueError("Review the HTTP/2 compatibility shim before changing the Tinker SDK version")
    import tinker._base_client as sdk_transport
    sdk_transport._default_pyqwest_transport = lambda: httpx.AsyncHTTPTransport(http2=True)
