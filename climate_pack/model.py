"""The site balances, worked out two ways.

`baseline` reproduces VillageOS's published formulas (Field Guide, Appendix D) exactly, so the two
results can be compared like for like. `climate_pack` keeps every one of those formulas and adds
what a hot, dry site needs:

- water supplies besides rain: treated wastewater reused for irrigation, groundwater up to a
  sustainable yield, and desalinated seawater where the site can reach the sea;
- the electricity those supplies take (desalination, reuse treatment, pumping);
- electricity for cooling, from the site's cooling degree days.

Nothing is rounded here; rounding belongs where figures are shown, as in VillageOS.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .assumptions import Assumption, resolve

HOURS_PER_DAY = 24
WATER_DENSITY_KG_PER_M3 = 1000.0
GRAVITY_M_PER_S2 = 9.81
JOULES_PER_KWH = 3.6e6


@dataclass(frozen=True)
class Site:
    """The site's own figures. Everything VillageOS would hold on the Site and its study."""

    name: str
    population: float
    built_footprint_hectares: float
    productive_footprint_hectares: float
    array_host_hectares: float
    rainfall_mm_per_year: float
    solar_resource_kwh_per_m2_per_year: float
    cooling_degree_days_per_year: float
    seawater_access: bool = True

    def __post_init__(self) -> None:
        for name in (
            "population", "built_footprint_hectares", "productive_footprint_hectares", "array_host_hectares",
            "rainfall_mm_per_year", "solar_resource_kwh_per_m2_per_year", "cooling_degree_days_per_year",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number")
            if value < 0:
                raise ValueError(f"{name} cannot be negative")


def _serve(demands: list[tuple[str, float]], supply: float) -> tuple[dict[str, float], float]:
    """Serve demands in order from one supply; answers what each took and what is left."""
    taken: dict[str, float] = {}
    for name, wanted in demands:
        take = min(wanted, supply)
        taken[name] = take
        supply -= take
    return taken, supply


def baseline(site: Site, profile: str = "villageos-default", overrides: dict[str, float] | None = None) -> dict:
    """VillageOS's own analysis, formula for formula (Appendix D)."""
    a = {k: v.value for k, v in resolve(profile, overrides).items()}

    harvest = site.built_footprint_hectares * site.rainfall_mm_per_year * a["runoffCoefficient"] * 10
    domestic = site.population * a["perCapitaConsumptionM3"]
    irrigation = site.productive_footprint_hectares * a["irrigationDemandM3PerHectarePerYear"]
    total = domestic + irrigation
    taken, _ = _serve([("domestic", domestic), ("irrigation", irrigation)], harvest)

    array_area = site.array_host_hectares * a["arrayCoverageFraction"] * 10_000
    generation = array_area * site.solar_resource_kwh_per_m2_per_year * a["moduleEfficiency"] * a["performanceRatio"] / 1000
    consumption = site.population * a["energyPerPersonKwhPerYear"] / 1000

    return {
        "water": {
            "harvestM3PerYear": harvest,
            "domesticDemandM3PerYear": domestic,
            "irrigationDemandM3PerYear": irrigation,
            "totalDemandM3PerYear": total,
            "percentOfWaterDemand": harvest / total * 100 if total else None,
            "domesticCoveredPercent": taken["domestic"] / domestic * 100 if domestic else None,
            "irrigationCoveredPercent": taken["irrigation"] / irrigation * 100 if irrigation else None,
            "shortfallM3PerYear": total - taken["domestic"] - taken["irrigation"],
        },
        "energy": {
            "solarPvAreaM2": array_area,
            "generationMwhPerYear": generation,
            "consumptionMwhPerYear": consumption,
            "percentOfConsumption": generation / consumption * 100 if consumption else None,
        },
    }


@dataclass
class _Source:
    name: str
    available: float
    kwh_per_m3: float
    potable: bool
    used: dict[str, float] = field(default_factory=dict)

    def take(self, demand: str, wanted: float) -> float:
        give = min(wanted, self.available)
        self.available -= give
        self.used[demand] = self.used.get(demand, 0.0) + give
        return give


def climate_pack(site: Site, profile: str = "villageos-default", overrides: dict[str, float] | None = None) -> dict:
    """The same site, with the water it can actually get and the energy it actually needs."""
    assumptions = resolve(profile, overrides)
    a = {k: v.value for k, v in assumptions.items()}
    base = baseline(site, profile, overrides)

    domestic = base["water"]["domesticDemandM3PerYear"]
    irrigation = base["water"]["irrigationDemandM3PerYear"]

    pump_kwh_per_m3 = (WATER_DENSITY_KG_PER_M3 * GRAVITY_M_PER_S2 * a["groundwaterLiftMetres"]) / a["pumpEfficiency"] / JOULES_PER_KWH
    reuse_available = domestic * a["wastewaterReturnFraction"] * a["reuseRecoveryFraction"]

    rain = _Source("rain", base["water"]["harvestM3PerYear"], 0.0, potable=True)
    ground = _Source("groundwater", a["groundwaterSustainableYieldM3PerYear"], pump_kwh_per_m3, potable=True)
    desal = _Source("desalination", float("inf") if site.seawater_access else 0.0, a["desalinationKwhPerM3"], potable=True)
    reuse = _Source("reuse", reuse_available, a["reuseTreatmentKwhPerM3"], potable=False)

    # Drinking water first, from potable sources in order of the energy each takes.
    # Irrigation next: recycled water first, then whatever potable supply is left.
    left = {"domestic": domestic, "irrigation": irrigation}
    for source in (rain, ground, desal):
        left["domestic"] -= source.take("domestic", left["domestic"])
    for source in (reuse, rain, ground, desal):
        left["irrigation"] -= source.take("irrigation", left["irrigation"])

    sources = {}
    water_energy_kwh = 0.0
    for source in (rain, ground, reuse, desal):
        volume = sum(source.used.values())
        energy = volume * source.kwh_per_m3
        water_energy_kwh += energy
        sources[source.name] = {
            "m3PerYear": volume,
            "kwhPerM3": source.kwh_per_m3,
            "mwhPerYear": energy / 1000,
            "toDomesticM3PerYear": source.used.get("domestic", 0.0),
            "toIrrigationM3PerYear": source.used.get("irrigation", 0.0),
        }

    cooling_kwh_per_person = (
        a["floorAreaPerPersonM2"] * a["envelopeConductanceWPerM2K"] * site.cooling_degree_days_per_year
        * HOURS_PER_DAY / 1000 / a["coolingCop"]
    )
    cooling_mwh = site.population * cooling_kwh_per_person / 1000
    water_energy_mwh = water_energy_kwh / 1000
    base_consumption = base["energy"]["consumptionMwhPerYear"]
    consumption = base_consumption + cooling_mwh + water_energy_mwh
    generation = base["energy"]["generationMwhPerYear"]
    total = domestic + irrigation
    shortfall = left["domestic"] + left["irrigation"]

    return {
        "water": {
            "sources": sources,
            "domesticDemandM3PerYear": domestic,
            "irrigationDemandM3PerYear": irrigation,
            "domesticCoveredPercent": (domestic - left["domestic"]) / domestic * 100 if domestic else None,
            "irrigationCoveredPercent": (irrigation - left["irrigation"]) / irrigation * 100 if irrigation else None,
            "percentOfWaterDemand": (total - shortfall) / total * 100 if total else None,
            "shortfallM3PerYear": shortfall,
            "desalinationCapacityM3PerDay": sources["desalination"]["m3PerYear"] / 365,
            "groundwaterPumpKwhPerM3": pump_kwh_per_m3,
        },
        "energy": {
            "generationMwhPerYear": generation,
            "baseConsumptionMwhPerYear": base_consumption,
            "coolingMwhPerYear": cooling_mwh,
            "coolingKwhPerPersonPerYear": cooling_kwh_per_person,
            "waterMwhPerYear": water_energy_mwh,
            "consumptionMwhPerYear": consumption,
            "percentOfConsumption": generation / consumption * 100 if consumption else None,
            "arrayAreaForNetPositiveM2": (
                consumption * 1000 / (site.solar_resource_kwh_per_m2_per_year * a["moduleEfficiency"] * a["performanceRatio"])
                if site.solar_resource_kwh_per_m2_per_year else None
            ),
        },
        "assumptions": {
            name: {"value": v.value, "unit": v.unit, "source": v.source, "sourced": v.sourced}
            for name, v in assumptions.items()
        },
    }


def compare(site: Site, profile: str, overrides: dict[str, float] | None = None) -> dict:
    """The VillageOS defaults, the region's demand on VillageOS's formulas, and the climate pack, side by side."""
    return {
        "site": site.name,
        "profile": profile,
        "villageosToday": baseline(site),
        "villageosWithRegionalDemand": baseline(site, profile, overrides),
        "climatePack": climate_pack(site, profile, overrides),
    }


def verdict(percent: float | None, target: float = 100.0) -> str:
    """VillageOS's three-way verdict: met, short, or not assessed."""
    if percent is None:
        return "not assessed"
    return "met" if percent >= target else "short of target"


__all__ = ["Site", "baseline", "climate_pack", "compare", "verdict", "Assumption"]
