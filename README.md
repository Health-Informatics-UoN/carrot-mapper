<p align="center">
  <a href="https://carrot.ac.uk/" target="_blank">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="/images/logo-dark.png">
    <img alt="Carrot Logo" src="/images/logo-primary.png" width="280"/>
  </picture>
  </a>
</p>

<p align="center">
<a href="https://github.com/Health-Informatics-UoN/Carrot-Mapper/actions/workflows/test.yml">
  <img src="https://github.com/Health-Informatics-UoN/Carrot-Mapper/actions/workflows/test.yml/badge.svg" alt="Test">
</a>
<a href="https://github.com/Health-Informatics-UoN/carrot-mapper/releases">
  <img src="https://img.shields.io/github/v/release/Health-Informatics-UoN/carrot-mapper" alt="Release">
</a>
<a href="https://opensource.org/license/mit">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</a>
</p>

<div align="center">
  <strong>
  <h2>Streamlined Data Mapping to OMOP</h2><br />
  <a href="https://carrot.ac.uk/">Carrot Mapper</a> automates vocabulary mapping and enables the reuse of mapping rules across datasets, offering advanced features to simplify OMOP data standardization tasks.<br /><br />
  </strong>
</div>

<p align="center">
  <br />
  <a href="https://health-informatics-uon.github.io/carrot/mapper" rel="dofollow"><strong>Explore the docs »</strong></a>
  <br />

<br />

<a href="https://carrot.ac.uk/">Carrot Mapper</a> is a webapp which allows the user to use the metadata (as output by [WhiteRabbit](https://github.com/OHDSI/WhiteRabbit)) from a dataset to produce mapping rules to the OMOP standard, in the JSON format. These can be ingested by [Carrot Transform](https://github.com/Health-Informatics-UoN/carrot-transform) to perform the mapping of the contents of the dataset to OMOP.

Carrot Mapper provides automated mapping from a selection of vocabularies, reuse of mapping rules across datasets, and manual mapping rule generation. It also provides a number of helpful features to support and encourage standardised mappings across datasets.

## Quick Start for Developers

To have the project up and running, please follow the [Quick Start Guide](https://health-informatics-uon.github.io/carrot/mapper/dev_guide/quickstart).

## License

This repository's source code is available under the [MIT license](LICENSE).
