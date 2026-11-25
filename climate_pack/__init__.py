"""Hot & arid climate pack for VillageOS: water beyond rain, and energy for cooling and water."""

from .assumptions import PROFILES, Assumption, resolve
from .model import Site, baseline, climate_pack, compare, verdict
from .sites import WILLOW_BEND_PROGRAMME, site_from_power

__all__ = [
    "PROFILES", "Assumption", "resolve", "Site", "baseline", "climate_pack", "compare", "verdict",
    "WILLOW_BEND_PROGRAMME", "site_from_power",
]
