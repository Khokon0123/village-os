"""The model reproduces VillageOS's own worked example before it adds anything.

LAND_INTAKE.md §8 works Willow Bend through by hand: 700 mm of rain, 1,750 kWh/m² of sun. If the
baseline here disagreed with those figures, every comparison after it would be meaningless.
"""

import json
from pathlib import Path

import pytest

from climate_pack import Site, baseline, climate_pack, site_from_power, verdict
from climate_pack.sites import willow_bend

DATA = Path(__file__).parent / "data"


@pytest.fixture
def willow():
    return willow_bend("Willow Bend", rainfall_mm=700, solar_kwh_m2=1750, cdd=0, seawater_access=False)


def test_baseline_reproduces_the_published_water_figures(willow):
    w = baseline(willow)["water"]
    assert w["harvestM3PerYear"] == pytest.approx(49_728)
    assert w["domesticDemandM3PerYear"] == pytest.approx(17_600)
    assert w["irrigationDemandM3PerYear"] == pytest.approx(40_800)
    assert w["percentOfWaterDemand"] == pytest.approx(85.15, abs=0.01)
    assert w["domesticCoveredPercent"] == pytest.approx(100)
    assert w["irrigationCoveredPercent"] == pytest.approx(78.7, abs=0.1)
    assert w["shortfallM3PerYear"] == pytest.approx(8_672)


def test_baseline_reproduces_the_published_energy_figures(willow):
    e = baseline(willow)["energy"]
    assert e["solarPvAreaM2"] == pytest.approx(3_168)
    assert e["generationMwhPerYear"] == pytest.approx(725.7, abs=0.1)
    assert e["consumptionMwhPerYear"] == pytest.approx(800)
    assert e["percentOfConsumption"] == pytest.approx(90.7, abs=0.1)


def test_with_no_heat_and_no_other_water_the_pack_agrees_with_the_baseline(willow):
    """No cooling degree days, no sea, no groundwater: the only new term is reuse, which helps irrigation."""
    pack = climate_pack(willow, overrides={"wastewaterReturnFraction": 0})
    base = baseline(willow)
    assert pack["water"]["percentOfWaterDemand"] == pytest.approx(base["water"]["percentOfWaterDemand"])
    assert pack["energy"]["consumptionMwhPerYear"] == pytest.approx(base["energy"]["consumptionMwhPerYear"])


def test_drinking_water_never_comes_from_reuse():
    site = willow_bend("dry", rainfall_mm=0, solar_kwh_m2=2000, cdd=0, seawater_access=False)
    sources = climate_pack(site)["water"]["sources"]
    assert sources["reuse"]["toDomesticM3PerYear"] == 0
    assert sources["reuse"]["toIrrigationM3PerYear"] > 0


def test_an_inland_site_reports_its_shortfall_rather_than_desalinating():
    site = willow_bend("inland", rainfall_mm=50, solar_kwh_m2=2000, cdd=3000, seawater_access=False)
    w = climate_pack(site)["water"]
    assert w["sources"]["desalination"]["m3PerYear"] == 0
    assert w["shortfallM3PerYear"] > 0


def test_a_coastal_site_closes_its_gap_with_desalination_and_pays_for_it_in_energy():
    site = willow_bend("coast", rainfall_mm=50, solar_kwh_m2=2000, cdd=0, seawater_access=True)
    pack = climate_pack(site)
    assert pack["water"]["shortfallM3PerYear"] == pytest.approx(0)
    desal = pack["water"]["sources"]["desalination"]
    assert pack["energy"]["waterMwhPerYear"] >= desal["m3PerYear"] * 4.0 / 1000


def test_cooling_energy_follows_degree_days():
    cool = climate_pack(willow_bend("a", 100, 2000, 1000, True))["energy"]["coolingMwhPerYear"]
    hot = climate_pack(willow_bend("b", 100, 2000, 3000, True))["energy"]["coolingMwhPerYear"]
    assert hot == pytest.approx(cool * 3)


def test_groundwater_pumping_energy_is_physics():
    # 1000 kg/m³ × 9.81 × 60 m ÷ 0.5 ÷ 3.6e6 J/kWh
    w = climate_pack(willow_bend("g", 100, 2000, 0, False), overrides={"groundwaterSustainableYieldM3PerYear": 10_000})["water"]
    assert w["groundwaterPumpKwhPerM3"] == pytest.approx(0.327, abs=0.001)
    assert w["sources"]["groundwater"]["m3PerYear"] == pytest.approx(10_000)


def test_every_assumption_says_where_it_came_from(willow):
    for name, a in climate_pack(willow, "uae")["assumptions"].items():
        assert a["source"], name


def test_a_site_states_its_own_value(willow):
    stated = climate_pack(willow, "uae", {"coolingCop": 4.5})["assumptions"]["coolingCop"]
    assert stated == {"value": 4.5, "unit": stated["unit"], "source": "Stated for this site", "sourced": True}


def test_unknown_profile_or_assumption_is_refused(willow):
    with pytest.raises(ValueError):
        climate_pack(willow, "mars")
    with pytest.raises(ValueError):
        climate_pack(willow, overrides={"nonsense": 1})


def test_negative_inputs_are_refused():
    with pytest.raises(ValueError):
        willow_bend("bad", rainfall_mm=-1, solar_kwh_m2=1, cdd=1, seawater_access=True)


def test_verdicts():
    assert verdict(None) == "not assessed"
    assert verdict(100) == "met"
    assert verdict(99.9) == "short of target"


@pytest.mark.parametrize("place", ["dubai", "jaipur"])
def test_real_power_data_reads(place):
    site = site_from_power(place, json.loads((DATA / f"power_{place}.json").read_text()), seawater_access=place == "dubai")
    assert isinstance(site, Site)
    assert site.cooling_degree_days_per_year > 1000
