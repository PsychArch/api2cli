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

### Minimax

Set your API key:

```bash
export MINIMAX_API_KEY="your_api_key_here"
```

Generate an image:

```bash
api2cli minimax image --prompt "A cinematic mountain sunrise" --output-file /tmp/mountain.png
```

Generate speech:

```bash
api2cli minimax tts --text "Hello from Minimax" --output-file /tmp/voice.mp3
```

### Jina

Set your API key (required for search):

```bash
export JINA_API_KEY="your_api_key_here"
```

Read a web page (cached on disk with TTL):

```bash
api2cli jina reader --url "https://example.com" --page 1
```

Search the web:

```bash
api2cli jina search --query "Jina AI search" --endpoint standard
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
