# Changelog

## v1.0 (unreleased)

Contributor to this version: Baptiste Hamon (@baptistehamon).

### Announcements
- The NZLUSDB website has been created ([GH#4](https://github.com/baptistehamon/nzlusdb/issues/4), [PR#3](https://github.com/baptistehamon/nzlusdb/pull/3)).

### Land Uses
- The following land use has been added:
  - Apple ([GH16#](https://github.com/baptistehamon/nzlusdb/issues/16), [PR#18](https://github.com/baptistehamon/nzlusdb/pull/18))
  - Avocado ([GH27#](https://github.com/baptistehamon/nzlusdb/issues/27), [PR#30](https://github.com/baptistehamon/nzlusdb/pull/30))
  - Blueberry ([GH25#](https://github.com/baptistehamon/nzlusdb/issues/25), [PR#26](https://github.com/baptistehamon/nzlusdb/pull/26))
  - Cherry ([GH29#](https://github.com/baptistehamon/nzlusdb/issues/29), [PR#34](https://github.com/baptistehamon/nzlusdb/pull/34))
  - Citrus ([GH9#](https://github.com/baptistehamon/nzlusdb/issues/9), [PR#13](https://github.com/baptistehamon/nzlusdb/pull/13))
  - Hops ([GH22#](https://github.com/baptistehamon/nzlusdb/issues/22), [PR#23](https://github.com/baptistehamon/nzlusdb/pull/23))
  - Kiwifruit ([GH28#](https://github.com/baptistehamon/nzlusdb/issues/28), [PR#32](https://github.com/baptistehamon/nzlusdb/pull/32))
  - Manuka ([GH#2](https://github.com/baptistehamon/nzlusdb/issues/2), [PR#8](https://github.com/baptistehamon/nzlusdb/pull/8))
  - Grapevines
    - Pinot Noir ([GH#35](https://github.com/baptistehamon/nzlusdb/issues/35), [PR#37](https://github.com/baptistehamon/nzlusdb/pull/37))
    - Sauvignon Blanc ([GH#35](https://github.com/baptistehamon/nzlusdb/issues/35), [PR#37](https://github.com/baptistehamon/nzlusdb/pull/37))
  - Early and late wheat ([GH#38](https://github.com/baptistehamon/nzlusdb/issues/38), [PR#42](https://github.com/baptistehamon/nzlusdb/pull/42))
  - Early and late maize ([GH#48](https://github.com/baptistehamon/nzlusdb/issues/48), [PR#51](https://github.com/baptistehamon/nzlusdb/pull/51)).

### Internal Changes
- A preprocessing step has been added enabling to preprocess criteria indicators before running the LSA ([GH9#](https://github.com/baptistehamon/nzlusdb/issues/9)).
- The Command Line Interface (CLI) has been improved ([GH9#](https://github.com/baptistehamon/nzlusdb/issues/9)).
- The README file has been updated ([GH10#](https://github.com/baptistehamon/nzlusdb/issues/10), [PR#15](https://github.com/baptistehamon/nzlusdb/pull/15)).
- The home page of the website has been updated ([GH10#](https://github.com/baptistehamon/nzlusdb/issues/10), [PR#15](https://github.com/baptistehamon/nzlusdb/pull/15)).
- The `day_full_bloom`, `frost_survival` and `sunburn_survival` indices and indicators have been added to support the computation apple climate indicators ([PR#18](https://github.com/baptistehamon/nzlusdb/pull/18)).
- The `downweight` and `downweight_season` functions have been added to support the computation of some climate indicators ([PR#18](https://github.com/baptistehamon/nzlusdb/pull/18)).
- The colorbar for suitability changes has been updated to avoid confusion ([GH#17](https://github.com/baptistehamon/nzlusdb/issues/17), [PR#19](https://github.com/baptistehamon/nzlusdb/pull/19)).
- The definition of the standardization function of `SuitabilityCriteria` has been updated reflecting `lsapy` v0.3.0 changes ([GH#20](https://github.com/baptistehamon/nzlusdb/issues/20), [PR#21](https://github.com/baptistehamon/nzlusdb/pull/21))
- The `chilling_hours` indicator has been added to support the computation of hops climate indicators ([PR#23](https://github.com/baptistehamon/nzlusdb/pull/23)).
- `func` and `fparams` arguments have been added to `indices.frost_survival` and `indices.sunburn_survival` to make them customizable ([PR#24](https://github.com/baptistehamon/nzlusdb/pull/24)).
- The `day_budbreak` indicator has been added to support the computation of kiwifruit climate indicators ([PR#32](https://github.com/baptistehamon/nzlusdb/pull/32)).
- The `cracking_survival` index and indicator have been added to support the computation of cherry climate indicators ([PR#34](https://github.com/baptistehamon/nzlusdb/pull/34)).
- The `chilling_hours` indicator has been modified to include both upper and lower temperature thresholds ([PR#37](https://github.com/baptistehamon/nzlusdb/pull/37)).
- The `heat_survival` index and indicator have been added to support the computation of grapevine climate indicators ([PR#37](https://github.com/baptistehamon/nzlusdb/pull/37)).
- The criteria indicator preprocessing functionality has been used to update allowing custom functions ([PR#42](https://github.com/baptistehamon/nzlusdb/pull/42)).
- The `decode_timedelta` of `xr.open_dataarray` in `nzlusdb.core.landuse.LandUse._load_indicator` has been set to `False` ([PR#42](https://github.com/baptistehamon/nzlusdb/pull/42)).
- The weight of maturity date criteria for wheat has been changed to 0.25 ([PR#49](https://github.com/baptistehamon/nzlusdb/pull/49)).
- The computation of flowering date for Pinot Noir and Sauvignon Blanc has been added ([PR#50](https://github.com/baptistehamon/nzlusdb/pull/50)).
- The `hot_days_frequency`, `cold_days`, and `cold_days_frequency` indices and indicators have been added to support the computation of maize climate indicators. ([PR#51](https://github.com/baptistehamon/nzlusdb/pull/51)).

### Bug Fixes
- Fix label error for projected suitability changes summary figures ([GH#11](https://github.com/baptistehamon/nzlusdb/issues/11), [PR#19](https://github.com/baptistehamon/nzlusdb/pull/19)).
- Fix standardization function parameters error for apple chill units criteria ([GH#31](https://github.com/baptistehamon/nzlusdb/issues/31), [PR#33](https://github.com/baptistehamon/nzlusdb/pull/33)).
- Fix cherry cracking survival indicator computation ([PR#36](https://github.com/baptistehamon/nzlusdb/pull/36)).
- Fix citrus and hops annual total precipitation indicator unit ([GH#39](https://github.com/baptistehamon/nzlusdb/issues/39), [PR#41](https://github.com/baptistehamon/nzlusdb/pull/41)).
- Fix computation of citrus and hops years rolling sum indicators ([GH#40](https://github.com/baptistehamon/nzlusdb/issues/40), [PR#41](https://github.com/baptistehamon/nzlusdb/pull/41)).
- Fix typo issue in grapevine documentation ([PR#43](https://github.com/baptistehamon/nzlusdb/pull/43)).
- The fruit cracking criteria for cherry has been removed considering unbias corrected relative humidity data ([GH#44](https://github.com/baptistehamon/nzlusdb/issues/44), [PR#45](https://github.com/baptistehamon/nzlusdb/pull/45)).
- Fix error in wheat phenological stages computation due to correction in [pynar package](https://forge.inrae.fr/agroclim/Indicators/OutilsPourIndicateurs/fonctionspython/pynar/-/merge_requests/17) and wheat suitability has been recomputed ([PR#49](https://github.com/baptistehamon/nzlusdb/pull/49)).
- Fix issue in maize and wheat phenological stages computation at 1km resolution ([PR#49](https://github.com/baptistehamon/nzlusdb/pull/49)).
