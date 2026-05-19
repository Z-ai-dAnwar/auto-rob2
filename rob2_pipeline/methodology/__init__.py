"""Canonical RoB 2 methodology guidance used by prompt rendering."""

from rob2_pipeline.methodology.domain1 import DOMAIN1_METHODOLOGY
from rob2_pipeline.methodology.domain2 import (
    DOMAIN2_ADHERING_METHODOLOGY,
    DOMAIN2_ASSIGNMENT_METHODOLOGY,
)
from rob2_pipeline.methodology.domain3 import DOMAIN3_METHODOLOGY
from rob2_pipeline.methodology.domain4 import DOMAIN4_METHODOLOGY
from rob2_pipeline.methodology.domain5 import DOMAIN5_METHODOLOGY

METHODOLOGIES = {
    "D1": DOMAIN1_METHODOLOGY,
    "D2_ASSIGNMENT": DOMAIN2_ASSIGNMENT_METHODOLOGY,
    "D2_ADHERING": DOMAIN2_ADHERING_METHODOLOGY,
    "D3": DOMAIN3_METHODOLOGY,
    "D4": DOMAIN4_METHODOLOGY,
    "D5": DOMAIN5_METHODOLOGY,
}

__all__ = [
    "DOMAIN1_METHODOLOGY",
    "DOMAIN2_ASSIGNMENT_METHODOLOGY",
    "DOMAIN2_ADHERING_METHODOLOGY",
    "DOMAIN3_METHODOLOGY",
    "DOMAIN4_METHODOLOGY",
    "DOMAIN5_METHODOLOGY",
    "METHODOLOGIES",
]
