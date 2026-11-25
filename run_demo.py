"""Place VillageOS's Willow Bend programme in Dubai and in Jaipur, and compare.

Climate normals come from NASA POWER (2001–2025 climatology), the same provider VillageOS's
`climate-averages` registration calls. Writes results/demo.json.
"""

import json
from pathlib import Path

from climate_pack import compare, site_from_power

HERE = Path(__file__).parent
SITES = [
    ("Dubai, UAE", "dubai", "uae", True),
    ("Jaipur, India", "jaipur", "india-urban", False),
]


def main() -> None:
    results = []
    for label, key, profile, coast in SITES:
        power = json.loads((HERE / "data" / f"power_{key}.json").read_text())
        site = site_from_power(label, power, seawater_access=coast)
        result = compare(site, profile)
        result["climate"] = {
            "rainfallMmPerYear": site.rainfall_mm_per_year,
            "solarKwhPerM2PerYear": site.solar_resource_kwh_per_m2_per_year,
            "coolingDegreeDays": site.cooling_degree_days_per_year,
            "seawaterAccess": coast,
            "coordinates": power["geometry"]["coordinates"][:2],
        }
        results.append(result)
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "demo.json").write_text(json.dumps(results, indent=2))
    for r in results:
        today, regional, pack = r["villageosToday"], r["villageosWithRegionalDemand"], r["climatePack"]
        print(f"\n== {r['site']} ({r['profile']}) climate {r['climate']}")
        print(f"  water: today {today['water']['percentOfWaterDemand']:.1f}%  regional {regional['water']['percentOfWaterDemand']:.1f}%  pack {pack['water']['percentOfWaterDemand']:.1f}%")
        print(f"  energy: today {today['energy']['percentOfConsumption']:.1f}%  pack {pack['energy']['percentOfConsumption']:.1f}%")
        print("  sources:", {k: round(v['m3PerYear']) for k, v in pack['water']['sources'].items()})
        print("  demand:", round(pack['water']['domesticDemandM3PerYear']), round(pack['water']['irrigationDemandM3PerYear']), "shortfall", round(pack['water']['shortfallM3PerYear']))
        e = pack["energy"]
        print(f"  energy MWh: gen {e['generationMwhPerYear']:.0f} base {e['baseConsumptionMwhPerYear']:.0f} cooling {e['coolingMwhPerYear']:.0f} water {e['waterMwhPerYear']:.0f} total {e['consumptionMwhPerYear']:.0f} arrays needed {e['arrayAreaForNetPositiveM2']:.0f} m2; desal {pack['water']['desalinationCapacityM3PerDay']:.0f} m3/day")


if __name__ == "__main__":
    main()
