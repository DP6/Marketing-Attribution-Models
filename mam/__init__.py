# Nova MAM package
from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("marketing_attribution_models")
except PackageNotFoundError:
    __version__ = "unknown"

from mam.preprocessing import (
    MAMPipeline,
    pipeline_format_1_to_unified,
    pipeline_format_2_to_unified,
    pipeline_format_3_to_unified,
)
from mam.core import MAM
from mam.results import AttributionResult
from mam.analysis import JAToolbox
from mam.models import (
    LastClickModel,
    FirstClickModel,
    LinearModel,
    PositionBasedModel,
    TimeDecayModel,
)
from mam.reporting import generate_report

__all__ = [
    "MAMPipeline",
    "pipeline_format_1_to_unified",
    "pipeline_format_2_to_unified",
    "pipeline_format_3_to_unified",
    "MAM",
    "AttributionResult",
    "JAToolbox",
    "LastClickModel",
    "FirstClickModel",
    "LinearModel",
    "PositionBasedModel",
    "TimeDecayModel",
    "generate_report",
]
