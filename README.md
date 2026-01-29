# api2cli

Convert APIs to CLI tools.

## Installation

```bash
pip install api2cli
```

Or with uv:

```bash
uv add api2cli
```

## Usage

```bash
api2cli --version
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install dependencies
uv sync

# Run the CLI
uv run api2cli --version
```

## Publishing

To publish a new version to PyPI:

1. Update the version in `src/api2cli/__init__.py` and `pyproject.toml`
2. Create and push a git tag:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
3. GitHub Actions will automatically build and publish to PyPI

## License

MIT
