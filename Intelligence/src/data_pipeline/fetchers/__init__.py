"""
Fetchers Package for FIN Data Pipeline.
"""

from .base import BaseFetcher, FetchResult
from .local import LocalBaselineFetcher, BaselineSourceAdapter
from .web import WebFetcher
from .myscheme_parser import MySchemeParser
from .sitemap import SitemapFetcher, SitemapDiff
from .pdf import PDFFetcher, PDFDocumentMetadata
from .huggingface import HuggingFaceFetcher, HFDatasetMetadata

__all__ = [
    "BaseFetcher",
    "FetchResult",
    "LocalBaselineFetcher",
    "BaselineSourceAdapter",
    "WebFetcher",
    "MySchemeParser",
    "SitemapFetcher",
    "SitemapDiff",
    "PDFFetcher",
    "PDFDocumentMetadata",
    "HuggingFaceFetcher",
    "HFDatasetMetadata",
]
