"""Build a Site from VillageOS's worked example and NASA POWER climate normals."""

from __future__ import annotations

from .model import Site

DAYS_PER_YEAR = 365.25

# Willow Bend, the invented 24-hectare, 320-person site VillageOS's LAND_INTAKE.md works through.
# Built footprint = residential + commercial + mobility; productive = food; arrays sit on residential.
WILLOW_BEND_PROGRAMME = {
    "parcelHectares": 24.0,
    "population": 320,
    "sharesPercent": {
        "residential": 22, "food-and-agriculture": 34, "green-water-restoration": 20,
        "commercial-retail": 8, "community-education-health": 9, "mobility-infrastructure": 7,
    },
}


def _hectares(share: float) -> float:
    total = sum(WILLOW_BEND_PROGRAMME["sharesPercent"].values())
    return share / total * WILLOW_BEND_PROGRAMME["parcelHectares"]


def willow_bend(name: str, rainfall_mm: float, solar_kwh_m2: float, cdd: float, seawater_access: bool) -> Site:
    shares = WILLOW_BEND_PROGRAMME["sharesPercent"]
    return Site(
        name=name,
        population=WILLOW_BEND_PROGRAMME["population"],
        built_footprint_hectares=_hectares(shares["residential"] + shares["commercial-retail"] + shares["mobility-infrastructure"]),
        productive_footprint_hectares=_hectares(shares["food-and-agriculture"]),
        array_host_hectares=_hectares(shares["residential"]),
        rainfall_mm_per_year=rainfall_mm,
        solar_resource_kwh_per_m2_per_year=solar_kwh_m2,
        cooling_degree_days_per_year=cdd,
        seawater_access=seawater_access,
    )


def site_from_power(name: str, power: dict, seawater_access: bool) -> Site:
    """Willow Bend's programme placed at a NASA POWER point.

    Reads the same two parameters VillageOS's `climate-averages` registration reads (PRECTOTCORR and
    ALLSKY_SFC_SW_DWN, both per day, times 365.25) plus CDD18_3, POWER's cooling degree days above 18.3 °C.
    """
    p = power["properties"]["parameter"]
    rainfall = p["PRECTOTCORR"]["ANN"] * DAYS_PER_YEAR
    solar = p["ALLSKY_SFC_SW_DWN"]["ANN"] * DAYS_PER_YEAR
    cdd = p["CDD18_3"]["ANN"]
    for label, value in (("PRECTOTCORR", rainfall), ("ALLSKY_SFC_SW_DWN", solar), ("CDD18_3", cdd)):
        if value is None or value < 0:  # POWER answers -999 for a value it does not hold
            raise ValueError(f"NASA POWER holds no {label} for {name}")
    return willow_bend(name, rainfall, solar, cdd, seawater_access)
