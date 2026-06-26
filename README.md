# datasanity

Data-quality checks for CSV, TSV, and Excel research/clinical tables.

This repository is a standalone Python package split from the ReproKit Suite. It can be installed, tested, versioned, and published independently.

## Install for development

```bash
git clone https://github.com/<your-user-or-org>/datasanity.git
cd datasanity
python -m pip install -e .[dev]
pytest
```

## Python API

```python
import datasanity
print(datasanity.__version__)
```

## CLI examples

```bash
datasanity check examples/messy_clinical_data.csv
```
```bash
datasanity check examples/messy_clinical_data.csv --format json
```

## Repository layout

```text
datasanity/
├── .github/workflows/tests.yml
├── docs/
├── examples/
├── src/datasanity/
├── tests/
├── pyproject.toml
├── README.md
└── LICENSE
```

## Status

Version `0.1.0` is an MVP intended for extension. The package includes a tested Python API and CLI.
