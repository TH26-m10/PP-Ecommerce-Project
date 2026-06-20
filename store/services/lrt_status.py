import json
import os
import urllib.error
import urllib.request


def fetch_lrt_proxy_status():
    """
    Read Least Response Time stats from the external Docker load balancer.
    Returns None when the proxy is not configured (local dev without Docker).
    """
    url = os.environ.get("LRT_PROXY_STATUS_URL", "").strip()
    if not url:
        return None

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return {"error": "LRT proxy unreachable", "url": url}
