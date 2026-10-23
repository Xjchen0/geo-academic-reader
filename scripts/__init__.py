"""geo-academic-reader core package."""

import warnings

# macOS system Python ships LibreSSL; urllib3 v2 warns loudly on import.
# Filter by message before importing urllib3 so the warning is caught.
warnings.filterwarnings("ignore", message=".*NotOpenSSLWarning.*")
warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")

from .version import __version__

__all__ = ["__version__"]
