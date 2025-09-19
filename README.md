# Meguru Streamlit App

Meguru is a scaffolded Streamlit application managed with Poetry. The current version ships with a basic four-tab layout ready for future development.

## Requirements

- Python 3.11+
- [Poetry](https://python-poetry.org/)

## Installation

```bash
poetry install
```

## Running the App

```bash
poetry run streamlit run app.py
```

By default the application falls back to bundled Google Maps sample data when
``GOOGLE_MAPS_API_KEY`` is not configured. To connect to the live services,
set the following environment variables before launching Streamlit:

```bash
export GOOGLE_MAPS_API_KEY="your-google-key"
export OPENAI_API_KEY="your-openai-key"
```

Set ``MEGURU_USE_GOOGLE_STUB=never`` if you always want to hit the live Google
Maps endpoints when the API key is configured.

## Testing

```bash
poetry run pytest
```
