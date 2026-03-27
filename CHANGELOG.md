# Changelog

All notable changes to this project will be documented in this file.

## [2026-03-27]

### Added
- Added three-page flow:
  - `/` homepage
  - `/start-analysis` input page
  - `/analysis-result` result page
- Added segmented visibility simulation comparison:
  - `all_visible`
  - `group_only`
  - `hide_selected`
- Added sensitive-tag expansion and corresponding backend risk factors.
- Added result-page detail pagination.
- Added action suggestion module in result page.

### Changed
- Changed audience input model from manual benefit/risk input to automatic estimation by audience type.
- Changed ratio input from numeric field to slider (percentage based).
- Changed scoring output to percentage score (0-100) while retaining raw utility value.
- Changed risk model from single-dimension to three-dimension risk profile:
  - misunderstanding risk
  - relationship risk
  - privacy risk
- Changed suggestion engine to include estimated score lift per suggestion (`estimatedDeltaScore`).
- Changed homepage to a centered landing layout with improved information hierarchy.

### Docs
- Updated `README.md` to reflect current architecture, routes, model logic, and latest capabilities.
- Added changelog entrypoint in `README.md`.
