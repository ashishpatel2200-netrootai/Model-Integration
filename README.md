# Model Selector

A lightweight local web application for selecting an LLM provider and model, then creating, copying, or downloading a JSON configuration. It uses only the Python standard library; no packages need to be installed.


<img width="1" height="1" alt="image" src="https://github.com/user-attachments/assets/ed2be8fc-4cda-47a7-8897-56f7973ecac6" />


## Start the app

From this project folder, run:

```bash
python3 main.py
```

The app starts a local web server and opens your browser at **http://127.0.0.1:8000/**. Keep the terminal open while using the app. Press **Ctrl+C** in that terminal to stop it.

If port 8000 is already in use, choose another port:

```bash
python3 main.py --port 8080
```

Then open **http://127.0.0.1:8080/**. You can also pass `--host` to bind another interface; by default the server only accepts connections from your computer.

## Choose a model

1. Select a provider: OpenAI, Anthropic, Google, Ollama, or OpenAI-compatible.
2. Choose a suggested **Model ID** or type an ID supported by your provider. Suggestions are starter values and may need updating as provider model names change.
3. For Ollama or OpenAI-compatible providers, optionally enter a **Base URL** such as `http://localhost:11434`.
4. Click **Create config** to display the generated JSON in the page.
5. Click **Copy config** to copy the selection to the clipboard, or **Download JSON** to save it as `model-config.json`.

The model ID is required. The app displays an error if you submit the form without one.

## Configuration format

For example, selecting OpenAI and `gpt-4o` creates:

```json
{
  "provider": "OpenAI",
  "api_type": "openai",
  "model": "gpt-4o"
}
```

When a base URL is provided for Ollama or OpenAI-compatible, it is included as `base_url`:

```json
{
  "provider": "Ollama",
  "api_type": "ollama",
  "model": "llama3.2",
  "base_url": "http://localhost:11434"
}
```

The app only prepares configuration; it does not connect to model providers, validate model IDs or endpoints, or send prompts. Set any required credentials in the application that consumes this JSON.
