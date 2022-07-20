# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
* `pylacoan run`, `parse` and `reparse` commands
* unparsable counts
* option not to choose any analysis
* `gramm` column for uniparser
* allow custom uniparser files
* punctuation stripping

### Fixed
* approved analyses are stored and loaded unambiguously

### Removed

### Changed
* more informed feedback
* uniparser: when not analysable, use unparsed wordform for object line
* segmentizer complains about unsuccessful conversion

## [0.0.1] (2022-03-22)
------------------

* First release on PyPI.


[Unreleased]: https://github.com/fmatter/pylacoan/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/fmatter/pylacoan/releases/tag/v0.0.1
