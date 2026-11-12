"""Local web app for choosing and exporting an LLM model configuration."""

from __future__ import annotations

import argparse
import errno
import html
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, TypedDict
from urllib.parse import parse_qs


class ProviderDetails(TypedDict):
    api_type: str
    models: list[str]
    default_model: str


PROVIDERS: dict[str, ProviderDetails] = {
    "OpenAI": {
        "api_type": "openai",
        "models": ["gpt-4o", "gpt-4o-mini", "o3", "o4-mini"],
        "default_model": "gpt-4o",
    },
    "Anthropic": {
        "api_type": "anthropic",
        "models": ["claude-sonnet-4-5", "claude-opus-4-1", "claude-haiku-4-5"],
        "default_model": "claude-sonnet-4-5",
    },
    "Google": {
        "api_type": "google",
        "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"],
        "default_model": "gemini-2.5-flash",
    },
    "Ollama": {
        "api_type": "ollama",
        "models": ["llama3.2", "qwen2.5", "mistral", "deepseek-r1"],
        "default_model": "llama3.2",
    },
    "OpenAI-compatible": {
        "api_type": "openai-compatible",
        "models": [],
        "default_model": "",
    },
}

PAGE_STYLE = """
<style>
  :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }
  * { box-sizing: border-box; }
  body { margin: 0; min-height: 100vh; padding: 48px 20px; color: #172033; background: #f3f5f9; }
  main { width: min(100%, 720px); margin: 0 auto; }
  .brand { display: inline-flex; align-items: center; gap: 10px; margin-bottom: 24px; color: #172033; font-size: 1.15rem; font-weight: 750; letter-spacing: -.04em; }
  .brand-mark { width: 34px; height: 34px; }
  .brand-name span { color: #344fcd; }
  .eyebrow { color: #596780; font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
  h1 { margin: 8px 0; font-size: clamp(2rem, 5vw, 2.7rem); letter-spacing: -.04em; }
  .intro { margin: 0 0 26px; color: #596780; line-height: 1.6; }
  .card { padding: 26px; border: 1px solid #e3e8f0; border-radius: 18px; background: white; box-shadow: 0 14px 40px #1720330c; }
  label { display: block; margin: 0 0 8px; font-size: .9rem; font-weight: 650; }
  input, select { width: 100%; min-height: 46px; padding: 10px 12px; border: 1px solid #cbd3df; border-radius: 9px; color: #172033; background: white; font: inherit; }
  input:focus, select:focus { outline: 3px solid #c9d8ff; border-color: #536fe5; }
  .field { margin-bottom: 20px; }
  .hint, .muted { color: #68758a; font-size: .85rem; line-height: 1.5; }
  .hint { margin: 8px 0 0; }
  .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
  button { min-height: 42px; padding: 0 16px; border: 1px solid #d3d9e4; border-radius: 9px; color: #26334a; background: #fff; font: inherit; font-weight: 650; cursor: pointer; }
  button:hover { background: #f4f6fa; }
  button.primary { border-color: #344fcd; color: white; background: #344fcd; }
  button.primary:hover { background: #293fae; }
  .preview { margin-top: 22px; }
  .preview h2 { margin: 0 0 10px; font-size: 1rem; }
  pre { overflow-x: auto; margin: 0; padding: 16px; border-radius: 10px; color: #e8edff; background: #172033; font: .9rem/1.55 ui-monospace, SFMono-Regular, Menlo, monospace; }
  .status { margin: 14px 0 0; color: #42516a; font-size: .9rem; }
  @media (max-width: 560px) { body { padding: 26px 14px; } .card { padding: 20px; } }
</style>
"""


def make_config(provider: str, model: str, base_url: str) -> dict[str, str]:
    """Validate submitted values and return the configuration document."""
    if provider not in PROVIDERS:
        raise ValueError("Choose a supported provider.")
    model = model.strip()
    if not model:
        raise ValueError("Enter a model ID before creating the configuration.")

    config = {
        "provider": provider,
        "api_type": str(PROVIDERS[provider]["api_type"]),
        "model": model,
    }
    base_url = base_url.strip()
    if base_url and provider in {"Ollama", "OpenAI-compatible"}:
        config["base_url"] = base_url
    return config


def render_page(
        provider: str = "OpenAI",
        model: str | None = None,
        base_url: str = "",
        config: dict[str, str] | None = None,
        status: str = "Choose a provider and model to get started.",
        error: str = "",
) -> bytes:
    """Render the selector form and an optional generated configuration."""
    provider = provider if provider in PROVIDERS else "OpenAI"
    if model is None:
        model = str(PROVIDERS[provider]["default_model"])

    provider_options = "\n".join(
        f'<option value="{html.escape(name, quote=True)}"'
        f'{" selected" if name == provider else ""}>{html.escape(name)}</option>'
        for name in PROVIDERS
    )
    models = PROVIDERS[provider]["models"]
    model_options = "\n".join(
        f'<option value="{html.escape(name, quote=True)}"></option>' for name in models
    )
    endpoint_style = "" if provider in {"Ollama", "OpenAI-compatible"} else ' style="display:none"'
    preview = ""
    if config is not None:
        preview = (
            '<section class="preview" aria-live="polite"><h2>Configuration preview</h2>'
            f'<pre id="config-preview">{html.escape(json.dumps(config, indent=2))}</pre></section>'
        )
    error_html = f'<p class="status" role="alert">{html.escape(error)}</p>' if error else ""
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Model Selector</title>
  {PAGE_STYLE}
</head>
<body>
  <main>
    <div class="brand" aria-label="Netroot AI">
      <svg class="brand-mark" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
        <path d="M20 20 10 10M20 20 30 10M20 20 10 30M20 20 30 30" fill="none" stroke="#344fcd" stroke-linecap="round" stroke-width="3" />
        <circle cx="20" cy="20" r="5" fill="#13a89e" />
        <circle cx="10" cy="10" r="4" fill="#344fcd" />
        <circle cx="30" cy="10" r="4" fill="#344fcd" />
        <circle cx="10" cy="30" r="4" fill="#13a89e" />
        <circle cx="30" cy="30" r="4" fill="#13a89e" />
      </svg>
      <span class="brand-name">Netroot<span>.ai</span></span>
    </div>
    <p class="eyebrow">Netroot AI DEMO Model Setup</p>
    <h1>Model selector</h1>
    <p class="intro">Choose a model provider and create a configuration you can copy or download.</p>
    <section class="card">
      <form method="post" action="/create" id="model-form">
        <div class="field">
          <label for="provider">Provider</label>
          <select id="provider" name="provider">{provider_options}</select>
        </div>
        <div class="field">
          <label for="model">Model ID</label>
          <input id="model" name="model" list="model-suggestions" value="{html.escape(model, quote=True)}" placeholder="Type a model ID" required>
          <datalist id="model-suggestions">{model_options}</datalist>
          <p class="hint">Suggestions are starting points. You can enter any model ID supported by your provider.</p>
        </div>
        <div class="field" id="endpoint-field"{endpoint_style}>
          <label for="base_url">Base URL <span class="muted">(optional)</span></label>
          <input id="base_url" name="base_url" type="url" value="{html.escape(base_url, quote=True)}" placeholder="http://localhost:11434">
        </div>
        <div class="actions">
          <button class="primary" type="submit">Create config</button>
          <button type="button" id="copy-button">Copy config</button>
          <button type="submit" formaction="/download">Download JSON</button>
        </div>
      </form>
      {preview}
      <p class="status" id="status" aria-live="polite">{html.escape(status)}</p>
      {error_html}
    </section>
  </main>
  <script>
    const providerModels = {json.dumps({name: value["models"] for name, value in PROVIDERS.items()})};
    const providerSelect = document.getElementById("provider");
    const modelInput = document.getElementById("model");
    const datalist = document.getElementById("model-suggestions");
    const endpointField = document.getElementById("endpoint-field");
    const status = document.getElementById("status");
    providerSelect.addEventListener("change", () => {{
      const provider = providerSelect.value;
      datalist.replaceChildren(...providerModels[provider].map((model) => {{
        const option = document.createElement("option");
        option.value = model;
        return option;
      }}));
      modelInput.value = providerModels[provider][0] || "";
      endpointField.style.display = ["Ollama", "OpenAI-compatible"].includes(provider) ? "block" : "none";
      status.textContent = provider + " selected.";
    }});
    document.getElementById("copy-button").addEventListener("click", async () => {{
      const form = new FormData(document.getElementById("model-form"));
      const provider = form.get("provider");
      const model = String(form.get("model") || "").trim();
      if (!model) {{ status.textContent = "Enter a model ID before copying the configuration."; modelInput.focus(); return; }}
      const apiTypes = {{"OpenAI":"openai", "Anthropic":"anthropic", "Google":"google", "Ollama":"ollama", "OpenAI-compatible":"openai-compatible"}};
      const config = {{provider, api_type: apiTypes[provider], model}};
      const baseUrl = String(form.get("base_url") || "").trim();
      if (baseUrl && ["Ollama", "OpenAI-compatible"].includes(provider)) config.base_url = baseUrl;
      try {{ await navigator.clipboard.writeText(JSON.stringify(config, null, 2)); status.textContent = "Configuration copied to the clipboard."; }}
      catch {{ status.textContent = "Clipboard access is unavailable. Create the config, then copy the preview manually."; }}
    }});
  </script>
</body>
</html>"""
    return document.encode("utf-8")


class ModelSelectorHandler(BaseHTTPRequestHandler):
    """Serve the model selector and its create/download actions."""

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(404, "Page not found")
            return
        self._send_html(render_page())

    def do_POST(self) -> None:
        if self.path not in {"/create", "/download"}:
            self.send_error(404, "Page not found")
            return
        length = min(int(self.headers.get("Content-Length", "0")), 16_384)
        form = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
        provider = form.get("provider", [""])[0]
        model = form.get("model", [""])[0]
        base_url = form.get("base_url", [""])[0]
        try:
            config = make_config(provider, model, base_url)
        except ValueError as exc:
            self._send_html(
                render_page(provider, model, base_url, status="Please correct the form and try again.", error=str(exc)),
                status=400,
            )
            return

        content = (json.dumps(config, indent=2) + "\n").encode("utf-8")
        if self.path == "/download":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="model-config.json"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        self._send_html(
            render_page(provider, model, base_url, config, "Configuration created. Copy it or download the JSON file.")
        )

    def _send_html(self, content: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def main() -> None:
    """

    :rtype: None
    """
    parser = argparse.ArgumentParser(description="Run the local model selector web app.")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    args = parser.parse_args()

    try:
        server = ThreadingHTTPServer((args.host, args.port), ModelSelectorHandler)
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        print(f"Port {args.port} is already in use; selecting an available port.")
        server = ThreadingHTTPServer((args.host, 0), ModelSelectorHandler)

    actual_port = server.server_address[1]
    url = f"http://{args.host}:{actual_port}/"
    print(f"Model Selector is running at {url}")
    print("Press Ctrl+C to stop the server.")
    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Model Selector.")
    finally:
        server.server_close()


if __name__ != "__main__":
    pass
else:
    main()
