# Changelog

## v1.0 (unreleased)

Contributor to this version: Baptiste Hamon (@baptistehamon).

### Announcements
- The NZLUSDB website has been created ([GH#4](https://github.com/baptistehamon/nzlusdb/issues/4), [PR#3](https://github.com/baptistehamon/nzlusdb/pull/3)).

### Land Uses
- The following land use has been added:
  - Apple ([GH16#](https://github.com/baptistehamon/nzlusdb/issues/16), [PR#18](https://github.com/baptistehamon/nzlusdb/pull/18))
  - Citrus ([GH9#](https://github.com/baptistehamon/nzlusdb/issues/9), [PR#13](https://github.com/baptistehamon/nzlusdb/pull/13))
  - Hops ([GH22#](https://github.com/baptistehamon/nzlusdb/issues/22), [PR#23](https://github.com/baptistehamon/nzlusdb/pull/23))
  - Manuka ([GH#2](https://github.com/baptistehamon/nzlusdb/issues/2), [PR#8](https://github.com/baptistehamon/nzlusdb/pull/8))

### Internal Changes
- A preprocessing step has been added enabling to preprocess criteria indicators before running the LSA ([GH9#](https://github.com/baptistehamon/nzlusdb/issues/9)).
- The Command Line Interface (CLI) has been improved ([GH9#](https://github.com/baptistehamon/nzlusdb/issues/9)).
- The README file has been updated ([GH10#](https://github.com/baptistehamon/nzlusdb/issues/10), [PR#15](https://github.com/baptistehamon/nzlusdb/pull/15)).
- The home page of the website has been updated ([GH10#](https://github.com/baptistehamon/nzlusdb/issues/10), [PR#15](https://github.com/baptistehamon/nzlusdb/pull/15)).
- The `day_full_bloom`, `frost_survival` and `sunburn_survival` indices and indicators, and  have been added to support the computation apple climate indicators ([PR#18](https://github.com/baptistehamon/nzlusdb/pull/18)).
- The `downweight` and `downweight_season` functions have been added to support the computation of some climate indicators ([PR#18](https://github.com/baptistehamon/nzlusdb/pull/18)).
- The colorbar for suitability changes has been updated to avoid confusion ([GH#17](https://github.com/baptistehamon/nzlusdb/issues/17), [PR#19](https://github.com/baptistehamon/nzlusdb/pull/19)).
- The definition of the standardization function of `SuitabilityCriteria` has been updated reflecting `lsapy` v0.3.0 changes ([GH#20](https://github.com/baptistehamon/nzlusdb/issues/20), [PR#21](https://github.com/baptistehamon/nzlusdb/pull/21))
- The `chill_hours` indicator has been added to support the computation of hops climate indicators ([GH#23](https://github.com/baptistehamon/nzlusdb/pull/23)).
- `func` and `fparams` arguments have been added to `indices.frost_survival` and `indices.sunburn_survival` to make them customizable ([GH#24](https://github.com/baptistehamon/nzlusdb/pull/24)).

### Bug Fixes
- Fix label error for projected suitability changes summary figures ([GH#11](https://github.com/baptistehamon/nzlusdb/issues/11), [PR#19](https://github.com/baptistehamon/nzlusdb/pull/19)).
