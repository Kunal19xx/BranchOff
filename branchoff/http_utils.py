"""
Small urllib wrapper used by the 'download' instance source. Isolated
here so instance_sources/download.py doesn't need to know about
redirect quirks or User-Agent spoofing.
"""

import re
import urllib.request

from .config import USER_AGENT

_installed = False


class HTTP308RedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_308(self, req, fp, code, msg, headers):
        # Override the 308 code with 301 to pass Python 3.7's internal
        # redirect_request checks.
        return self.http_error_301(req, fp, 301, msg, headers)


def install_redirect_handler():
    """Idempotent: safe to call multiple times."""
    global _installed
    if not _installed:
        urllib.request.install_opener(
            urllib.request.build_opener(HTTP308RedirectHandler)
        )
        _installed = True


def http_get(url, timeout=30):
    install_redirect_handler()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_head_size(url, timeout=15):
    """
    Return the remote file size in bytes, or None if unavailable.

    miplib.zib.de rejects/mishandles plain HEAD requests, so instead we
    do a GET for just the first byte via a Range header (servers that
    honor it reply 206 with a Content-Range: bytes 0-0/<total> header;
    servers that ignore Range just reply 200 with the normal
    Content-Length, which we fall back to). Either way we don't pull
    the whole file down just to measure it.
    """
    install_redirect_handler()
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            cr = resp.headers.get("Content-Range")
            if cr:
                m = re.search(r"/(\d+)\s*$", cr)
                if m:
                    return int(m.group(1))
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl is not None else None
    except Exception:
        # last-resort fallback: a plain GET, reading only headers
        try:
            req2 = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT}, method="HEAD"
            )
            with urllib.request.urlopen(req2, timeout=timeout) as resp:
                cl = resp.headers.get("Content-Length")
                return int(cl) if cl is not None else None
        except Exception:
            return None
