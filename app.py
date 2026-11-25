"""VillageOS ClimatePack — a pipeline node for hot, dry sites.

A Python node on the VillageOS service contract (docs/SERVICES.md §16), built the way
vos.Service.Python.Echo is: the contract lives in vos.Service.Python.Shared, and this file adds the
operation. It sits beside the EnergyBalance and WaterReserve nodes: wire a study's figures in, and
it answers the water each source supplies, the desalination capacity a site needs, and the
electricity for cooling and for water that the shared study does not yet count.

It writes nothing but its answer, so a rehearsal may call it.

Run:  .venv/bin/python app.py --port=5110 --myceliumUrl=https://localhost:7243
"""

from __future__ import annotations

import sys

from climate_pack import PROFILES, Site, climate_pack
from climate_pack.assumptions import PACK_DEFAULTS, VILLAGEOS_DEFAULTS
from vos_service import Config, NodeService, Port, ServiceHost, Setting, parse_args

SERVICE_NAME = "ClimatePack"

SITE_PORTS = [
    "population",
    "builtFootprintHectares",
    "productiveFootprintHectares",
    "arrayHostHectares",
    "rainfallMillimetresPerYear",
    "solarResourceKwhPerM2PerYear",
    "coolingDegreeDaysPerYear",
]
ASSUMPTION_PORTS = sorted({**VILLAGEOS_DEFAULTS, **PACK_DEFAULTS})

OUTPUTS = {
    "percentOfWaterDemand": "number",
    "shortfallM3PerYear": "number",
    "desalinationM3PerYear": "number",
    "desalinationCapacityM3PerDay": "number",
    "reuseM3PerYear": "number",
    "groundwaterM3PerYear": "number",
    "coolingMwhPerYear": "number",
    "waterMwhPerYear": "number",
    "consumptionMwhPerYear": "number",
    "percentOfConsumption": "number",
    "arrayAreaForNetPositiveM2": "number",
    "unsourcedAssumptions": "string",
}


def _number(context, port: str) -> float:
    value = context.input(port)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # A port wired to a withheld derived property arrives present but null: name the port.
        raise ValueError(f"{SERVICE_NAME} node requires a numeric '{port}' input")
    return float(value)


def run(context) -> dict:
    profile = context.param("profile") or "villageos-default"
    access = context.param("seawaterAccess")
    seawater_access = True if access is None else access in (True, "true", "True")
    site = Site(
        name=str(context.input("siteName") or "site"),
        population=_number(context, "population"),
        built_footprint_hectares=_number(context, "builtFootprintHectares"),
        productive_footprint_hectares=_number(context, "productiveFootprintHectares"),
        array_host_hectares=_number(context, "arrayHostHectares"),
        rainfall_mm_per_year=_number(context, "rainfallMillimetresPerYear"),
        solar_resource_kwh_per_m2_per_year=_number(context, "solarResourceKwhPerM2PerYear"),
        cooling_degree_days_per_year=_number(context, "coolingDegreeDaysPerYear"),
        seawater_access=seawater_access,
    )
    overrides = {port: _number(context, port) for port in ASSUMPTION_PORTS if context.input(port) is not None}
    result = climate_pack(site, profile, overrides)
    water, energy, sources = result["water"], result["energy"], result["water"]["sources"]
    unsourced = sorted(name for name, a in result["assumptions"].items() if not a["sourced"])
    return {
        "percentOfWaterDemand": water["percentOfWaterDemand"],
        "shortfallM3PerYear": water["shortfallM3PerYear"],
        "desalinationM3PerYear": sources["desalination"]["m3PerYear"],
        "desalinationCapacityM3PerDay": water["desalinationCapacityM3PerDay"],
        "reuseM3PerYear": sources["reuse"]["m3PerYear"],
        "groundwaterM3PerYear": sources["groundwater"]["m3PerYear"],
        "coolingMwhPerYear": energy["coolingMwhPerYear"],
        "waterMwhPerYear": energy["waterMwhPerYear"],
        "consumptionMwhPerYear": energy["consumptionMwhPerYear"],
        "percentOfConsumption": energy["percentOfConsumption"],
        "arrayAreaForNetPositiveM2": energy["arrayAreaForNetPositiveM2"],
        "unsourcedAssumptions": ", ".join(unsourced),
    }


node = NodeService(
    run,
    [Port.input("siteName", "string")]
    + [Port.input(p, "number", required=True) for p in SITE_PORTS]
    + [Port.input(p, "number") for p in ASSUMPTION_PORTS]
    + [Port.output(name, kind) for name, kind in OUTPUTS.items()],
    rehearses=True,
    settings=[
        Setting("profile", values=sorted(PROFILES), default="villageos-default"),
        Setting("seawaterAccess", values=[True, False], default=True),
    ],
)

config = parse_args(sys.argv[1:]) or Config()
host = ServiceHost(SERVICE_NAME, config, node.handle, title="VillageOS ClimatePack node")
node.mount(host)
app = host.app


def main() -> None:
    host.run("app.py")


if __name__ == "__main__":
    main()
