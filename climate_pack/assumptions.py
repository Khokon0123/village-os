"""Every number the climate pack assumes, with where it came from.

VillageOS's own rule is that a figure says where it came from. Each assumption here carries a
`source`, or says plainly that none is recorded yet. Those are the values a summer of research
would pin down.

A profile is a set of assumptions for one region. A site states its own value to override any of
them, exactly as a VillageOS study overrides what it inherits from the shared SiteStudy kind.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Assumption:
    value: float
    unit: str
    source: str  # a citation, or "No source recorded" when none is

    @property
    def sourced(self) -> bool:
        return not self.source.startswith("No source recorded")


NO_SOURCE = "No source recorded — to be sourced"

# The values VillageOS ships on its shared SiteStudy kind (Field Guide, Appendix D).
VILLAGEOS_DEFAULTS: dict[str, Assumption] = {
    "runoffCoefficient": Assumption(0.8, "fraction", "VillageOS Field Guide, Appendix D (no source recorded there)"),
    "perCapitaConsumptionM3": Assumption(55.0, "m³/person/yr", "VillageOS Field Guide, Appendix D: 150 L/day (no source recorded there)"),
    "irrigationDemandM3PerHectarePerYear": Assumption(5000.0, "m³/ha/yr", "VillageOS Field Guide, Appendix D (no source recorded there)"),
    "energyPerPersonKwhPerYear": Assumption(2500.0, "kWh/person/yr", "VillageOS Field Guide, Appendix D (no source recorded there)"),
    "moduleEfficiency": Assumption(0.17, "fraction", "VillageOS Field Guide, Appendix D (no source recorded there)"),
    "performanceRatio": Assumption(0.77, "fraction", "VillageOS Field Guide, Appendix D (no source recorded there)"),
    "arrayCoverageFraction": Assumption(0.06, "fraction", "VillageOS Field Guide, Appendix D (no source recorded there)"),
}

# What the climate pack adds. Shared by every profile unless a profile overrides it.
PACK_DEFAULTS: dict[str, Assumption] = {
    "desalinationKwhPerM3": Assumption(
        4.0, "kWh/m³",
        "Schunke et al. (2020), Frontiers in Sustainable Cities 2:9 — typical SWRO 3.5–4.5 kWh/m³; midpoint taken",
    ),
    "reuseTreatmentKwhPerM3": Assumption(
        1.5, "kWh/m³",
        "Schunke et al. (2020) — indirect potable reuse 1.5–2.0 kWh/m³; low end taken, since irrigation reuse needs less treatment",
    ),
    "wastewaterReturnFraction": Assumption(0.8, "fraction of domestic water", NO_SOURCE + " (a common design value)"),
    "reuseRecoveryFraction": Assumption(0.9, "fraction of wastewater", NO_SOURCE),
    "groundwaterSustainableYieldM3PerYear": Assumption(0.0, "m³/yr", "Site-specific; 0 until a hydrogeological figure is stated for the site"),
    "groundwaterLiftMetres": Assumption(60.0, "m", NO_SOURCE),
    "pumpEfficiency": Assumption(0.5, "fraction", NO_SOURCE),
    "floorAreaPerPersonM2": Assumption(30.0, "m²/person", NO_SOURCE),
    "envelopeConductanceWPerM2K": Assumption(1.0, "W/(m² floor·K)", NO_SOURCE),
    "coolingCop": Assumption(3.0, "kWh cooling per kWh electricity", NO_SOURCE),
}

PROFILES: dict[str, dict[str, Assumption]] = {
    "villageos-default": {},
    "uae": {
        "perCapitaConsumptionM3": Assumption(
            200.9, "m³/person/yr",
            "Khaleej Times (22 Mar 2016), citing FEWA: 550 L/day per UAE resident",
        ),
    },
    "india-urban": {
        "perCapitaConsumptionM3": Assumption(
            49.3, "m³/person/yr",
            "CPHEEO design norm: 135 L/day for cities with sewerage (NCRPB repository, clause 2.2.8)",
        ),
    },
}


def resolve(profile: str, overrides: dict[str, float] | None = None) -> dict[str, Assumption]:
    """The assumptions for a profile: VillageOS's, then the pack's, then the profile's, then the site's own."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile '{profile}'; known: {', '.join(sorted(PROFILES))}")
    merged = {**VILLAGEOS_DEFAULTS, **PACK_DEFAULTS, **PROFILES[profile]}
    for name, value in (overrides or {}).items():
        if name not in merged:
            raise ValueError(f"unknown assumption '{name}'")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"assumption '{name}' must be a number")
        merged[name] = Assumption(float(value), merged[name].unit, "Stated for this site")
    return merged
