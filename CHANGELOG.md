# Changelog

All notable changes to this project will be documented in this file.

## [0.1.2] - 2025-04-08
### Fixed
- Improved default note type selection in prompts
- Updated dependencies and added related projects to README

## [0.1.1] - 2025-04-08
### Added
- Platform support check for background Anki launch
- Improved deck and note type selection experience
- Improved note type selection and compatibility checking
- SRT subtitle file processing support
- Support for Anki-style sound field values
- CI/CD workflows and enhanced documentation
- Publish and clean commands to justfile
- Tag customization for Anki notes
- Language detection for automatic translation
- --launch-anki option and automatic Anki launching
- Support for CSV/TSV file import for bulk vocabulary adding
- Direct specification of CSV/TSV files as an argument
- Note type detection and saved configuration
- Pre-commit hooks for code formatting
- Renamed project from langki to add2anki
- Dry-run and verbose modes for CLI
- Enhanced translation style documentation and style parameter to tests

### Changed
- Reorganized CLI code and improved note type display
- Extracted context-aware language into new package
- Improved code quality and type annotations
- Improved audio handling and expanded pre-commit configuration
- Improved sort field detection with fallback mechanism
- Reformat configs, update tasks, and bump dependency versions
- Added license and project URLs to pyproject.toml
- Improved README installation instructions
- Updated Python requirement to 3.11

### Fixed
- Prevented audio generation in dry-run mode
- Removed trailing whitespace

## [0.1.0] - 2025-03-11
### Added
- Initial project setup as langki

---

> This changelog was generated from git commit messages and version bumps in pyproject.toml.
