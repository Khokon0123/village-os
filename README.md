# VillageOS ClimatePack — water and energy for hot, dry sites

A prototype pipeline node for [VillageOS](https://github.com/ReGen-Villages/VillageOS-API), built on
its Python service contract, by Khokon Barua (Ohio Wesleyan University).

## The gap

VillageOS's site analysis (Field Guide, Appendix D) counts one water supply, rain falling on hard
surfaces, and one energy demand, a flat 2,500 kWh per resident. That is right for a temperate site.
For a hot, dry one it gets both verdicts wrong:

- **Water.** A Dubai site gets about 84 mm of rain a year, so the rain harvest covers about a tenth
  of demand and the site reads as failing. Real Gulf communities run on desalinated seawater and
  recycled wastewater, which the analysis has no place for.
- **Energy.** Air conditioning dominates electricity use in the Gulf and much of India. VillageOS
  already folds cooling need into its climate charts, but none of it reaches the energy balance, and
  neither does the electricity desalination and water treatment take.

## What it adds

| Addition | How |
| --- | --- |
| Recycled wastewater | A share of domestic water returns as wastewater and is treated for irrigation only; drinking water never comes from reuse |
| Groundwater | Up to a sustainable yield the site states (0 until one is stated), with pumping energy from physics: ρ·g·lift ÷ pump efficiency |
| Desalination | Closes the remaining gap where the site reaches the sea, and reports the plant size it needs; an inland site reports its shortfall instead |
| Water energy | Each source's volume × its energy per cubic metre, added to the site's consumption |
| Cooling energy | Floor area per person × envelope conductance × cooling degree days × 24 h ÷ AC efficiency |
| Regional profiles | `uae`, `india-urban`, and `villageos-default`; a site states its own value for any assumption |

Every assumption carries its source, or says *no source recorded*, the way VillageOS's own appendix
does. The unsourced ones are the open research questions.

## It agrees with VillageOS first

`test_model.py` reproduces the Willow Bend worked example in LAND_INTAKE.md §8 exactly (harvest
49,728 m³, irrigation short 8,672 m³, 91% of consumption) before it changes anything. With no heat,
no sea and no reuse, the pack gives the baseline's answers.

## Results: Willow Bend's programme in Dubai and Jaipur

Same 24 ha, 320-person programme as VillageOS's example; climate from NASA POWER (2001–2025
normals), the provider VillageOS's own `climate-averages` registration calls.

| | Dubai (coast) | Jaipur (inland) |
| --- | --- | --- |
| Rain / cooling degree days | 84 mm / 3,778 | 526 mm / 3,024 |
| Water covered — VillageOS today | 10% | 64% |
| Water covered — climate pack | 100% (desal 160 m³/day, reuse covers all irrigation) | 86% (7,853 m³/yr still short) |
| Energy — VillageOS today | 107%, net positive | 103%, net positive |
| Energy — climate pack | 62%, short | 79%, short |
| Array area to be net positive | 5,103 m² (estimate holds 3,168) | 4,038 m² |

Both verdicts flip for Dubai: the water problem has a known engineering answer, and the real
shortfall is energy.

## Run

Put this folder in a VillageOS-API checkout as `vos.Service.Python.ClimatePack`, then:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest          # 20 tests
.venv/bin/python run_demo.py        # writes results/demo.json
.venv/bin/python app.py --port=5110 --myceliumUrl=https://localhost:7243
```

`GET /manifest` declares the node's ports and its two settings, `profile` and `seawaterAccess`.

## Also here

- `seed/cooling-degree-days.registration.json` — a draft Tributary registration that fetches cooling
  degree days the same way `climate-averages` fetches rainfall. Not yet run through the seed validator.

## Limits, and what a summer would settle

- Annual totals hide seasons: Jaipur's rain falls in a few monsoon months, so storage sizing needs
  the daily rain VillageOS already fetches.
- Cooling uses a simple degree-day model; humidity, building type and the study's wet-bulb figures
  should refine it.
- Several assumptions (AC efficiency, floor area per person, wastewater return, pump lift) have no
  regional source yet. Pinning them for India and the UAE, with citations, is the research.
- The pack is a pipeline node today. Folded into the platform, its formulas would become derived
  properties on the shared study, judged by ranges like every other balance.

## License

AGPL-3.0-or-later, matching VillageOS-API.
