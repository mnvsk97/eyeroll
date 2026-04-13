"""CLI entry point for eyeroll."""

import json
import os
import sys

import click
from dotenv import load_dotenv

_ENV_PATH = os.path.join(os.path.expanduser("~"), ".eyeroll", ".env")
load_dotenv(_ENV_PATH)
load_dotenv()


@click.group()
def cli():
    """eyeroll — AI eyes that roll through video. Watch, understand, act."""


@cli.command()
def init():
    """Set up eyeroll — choose a backend and configure API key."""
    env_dir = os.path.dirname(_ENV_PATH)
    os.makedirs(env_dir, exist_ok=True)

    # Ask which backend
    click.echo("Which backend do you want to use?\n")
    click.echo("  1. gemini  — Google Gemini Flash API (fast, cheap, best quality)")
    click.echo("  2. openai  — OpenAI GPT-4o (great vision, Whisper audio)")
    click.echo("  3. ollama  — Local models via Ollama (private, no API key)\n")

    choice = click.prompt("Choose", type=click.Choice(["1", "2", "3"]), default="1")
    backend_map = {"1": "gemini", "2": "openai", "3": "ollama"}
    backend = backend_map[choice]

    if backend == "ollama":
        click.echo("\nOllama needs no API key. Make sure Ollama is running:")
        click.echo("  ollama serve")
        click.echo(f"\nSaving backend preference...")
        _save_env("EYEROLL_BACKEND", backend)
        click.secho("Setup complete. Run `eyeroll watch <video>` to get started.", fg="green")
        return

    if backend == "gemini":
        _setup_gemini()
    else:
        _setup_openai()

    _save_env("EYEROLL_BACKEND", backend)
    click.secho("Setup complete. Run `eyeroll watch <video>` to get started.", fg="green")


def _setup_gemini():
    """Configure Gemini — API key or service account credentials."""
    existing_key = os.environ.get("GEMINI_API_KEY")
    existing_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    eyeroll_creds = os.path.join(os.path.expanduser("~"), ".eyeroll", "credentials.json")
    has_creds = existing_creds or os.path.isfile(eyeroll_creds)

    if existing_key or has_creds:
        source = "GEMINI_API_KEY" if existing_key else "credentials.json"
        if not click.confirm(f"\nGoogle credentials already configured ({source}). Overwrite?", default=False):
            return

    click.echo("\nHow do you want to authenticate with Google?\n")
    click.echo("  1. API key         — get one at https://aistudio.google.com/apikey")
    click.echo("  2. credentials.json — service account for Vertex AI\n")

    auth_choice = click.prompt("Choose", type=click.Choice(["1", "2"]), default="1")

    if auth_choice == "1":
        api_key = click.prompt(
            "Enter your Gemini API key\n"
            "  (input is hidden)",
            hide_input=True,
        )
        _save_env("GEMINI_API_KEY", api_key)
        os.environ["GEMINI_API_KEY"] = api_key

        click.echo("Validating API key...")
        try:
            _validate_gemini(api_key)
        except Exception as e:
            click.secho(f"Validation failed: {e}", fg="red", err=True)
            raise SystemExit(1)
    else:
        creds_path = click.prompt(
            "Path to your credentials.json\n"
            "  (service account key file)",
        )
        creds_path = os.path.expanduser(creds_path.strip())
        if not os.path.isfile(creds_path):
            click.secho(f"File not found: {creds_path}", fg="red", err=True)
            raise SystemExit(1)

        # Save the path so the backend finds it
        _save_env("GOOGLE_APPLICATION_CREDENTIALS", creds_path)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        click.echo(f"Saved credentials path: {creds_path}")

        click.echo("Validating service account...")
        try:
            _validate_gemini_service_account(creds_path)
        except Exception as e:
            click.secho(f"Validation failed: {e}", fg="red", err=True)
            raise SystemExit(1)


def _setup_openai():
    """Configure OpenAI API key."""
    existing_key = os.environ.get("OPENAI_API_KEY")
    if existing_key:
        if not click.confirm(f"\nOPENAI_API_KEY already set. Overwrite?", default=False):
            return

    api_key = click.prompt(
        "Enter your OpenAI API key\n"
        "  Get one at https://platform.openai.com/api-keys\n"
        "  (input is hidden)",
        hide_input=True,
    )
    _save_env("OPENAI_API_KEY", api_key)
    os.environ["OPENAI_API_KEY"] = api_key

    click.echo("Validating API key...")
    try:
        _validate_openai(api_key)
    except Exception as e:
        click.secho(f"Validation failed: {e}", fg="red", err=True)
        raise SystemExit(1)


def _save_env(key: str, value: str) -> None:
    """Append or update a key in ~/.eyeroll/.env."""
    env_dir = os.path.dirname(_ENV_PATH)
    os.makedirs(env_dir, exist_ok=True)

    lines = []
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH) as f:
            lines = [line for line in f.readlines() if not line.startswith(f"{key}=")]
    lines.append(f"{key}={value}\n")
    with open(_ENV_PATH, "w") as f:
        f.writelines(lines)


def _validate_gemini(api_key: str) -> None:
    """Validate a Gemini API key."""
    try:
        from google import genai
    except ImportError:
        click.secho(
            "Gemini SDK not installed. Run: pip install eyeroll[gemini]",
            fg="red", err=True,
        )
        raise SystemExit(1)
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Say 'ok' if you can read this.",
    )
    if not response.text:
        raise RuntimeError("API key accepted but got empty response.")


def _validate_gemini_service_account(creds_path: str) -> None:
    """Validate a Gemini service account credentials file."""
    try:
        from google import genai
        from google.oauth2 import service_account
    except ImportError:
        click.secho(
            "Gemini SDK not installed. Run: pip install eyeroll[gemini]",
            fg="red", err=True,
        )
        raise SystemExit(1)

    import json
    credentials = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    with open(creds_path) as f:
        project_id = json.load(f).get("project_id")

    client = genai.Client(
        vertexai=True,
        credentials=credentials,
        project=project_id,
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
    from google.genai import types
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=types.Content(role="user", parts=[
            types.Part(text="Say 'ok' if you can read this."),
        ]),
    )
    if not response.text:
        raise RuntimeError("Credentials accepted but got empty response.")


def _validate_openai(api_key: str) -> None:
    """Validate an OpenAI API key."""
    try:
        from openai import OpenAI
    except ImportError:
        click.secho(
            "OpenAI SDK not installed. Run: pip install eyeroll[openai]",
            fg="red", err=True,
        )
        raise SystemExit(1)
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Say 'ok' if you can read this."}],
        max_tokens=5,
    )
    if not response.choices[0].message.content:
        raise RuntimeError("API key accepted but got empty response.")


@cli.command()
@click.argument("source")
@click.option("--context", "-c", default=None,
              help="Additional context (Slack message, issue description, what to do with the video, etc.)")
@click.option("--max-frames", default=20, show_default=True,
              help="Maximum key frames to analyze from video.")
@click.option("--backend", "-b", type=click.Choice(["gemini", "openai", "ollama"]), default=None,
              help="Vision backend. Defaults to EYEROLL_BACKEND env var, then gemini.")
@click.option("--model", "-m", default=None,
              help="Model override (e.g., qwen3-vl:8b for ollama, gemini-2.0-flash for gemini).")
@click.option("--codebase-context", "-cc", default=None,
              help="Codebase context (inline text or path to a file like .eyeroll/context.md).")
@click.option("--parallel", "-p", default=None, type=int,
              help="Concurrent workers for frame analysis. Default: 3 for ollama, 1 for others.")
@click.option("--no-cache", is_flag=True, help="Skip cache and force fresh analysis.")
@click.option("--output", "-o", default=None,
              help="Write output to file instead of stdout.")
@click.option("--verbose", "-v", is_flag=True, help="Show progress details.")
def watch(source, context, codebase_context, max_frames, backend, model, parallel, no_cache, output, verbose):
    """Analyze a video/screenshot and produce structured notes.

    SOURCE can be a URL (YouTube, Loom, etc.) or a local file path.

    \b
    Backends:
      gemini   Google Gemini Flash API (default, requires GEMINI_API_KEY)
      openai   OpenAI GPT-4o (requires OPENAI_API_KEY)
      ollama   Local models via Ollama (e.g., qwen3-vl, no API key needed)

    \b
    Examples:
      eyeroll watch https://loom.com/share/abc123
      eyeroll watch ./recording.mp4 --context "checkout broken after PR #432"
      eyeroll watch demo.mp4 -c "create a skill from this" --backend ollama
      eyeroll watch screenshot.png -b ollama -m qwen3-vl:2b
    """
    from .watch import watch as run_watch

    # --model without --backend: infer backend from model name
    if model and not backend:
        if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            backend = "openai"
        elif not model.startswith("gemini"):
            backend = "ollama"

    # Default parallel workers: 3 for API backends (separate servers), 1 for ollama (single GPU)
    if parallel is None:
        effective_backend = backend or os.environ.get("EYEROLL_BACKEND", "gemini")
        parallel = 1 if effective_backend == "ollama" else 3

    # Resolve --codebase-context: if it's a file path, read it
    if codebase_context and os.path.isfile(os.path.expanduser(codebase_context)):
        with open(os.path.expanduser(codebase_context)) as f:
            codebase_context = f.read()

    try:
        report = run_watch(
            source=source,
            context=context,
            codebase_context=codebase_context,
            max_frames=max_frames,
            backend_name=backend,
            model=model,
            verbose=verbose,
            no_cache=no_cache,
            parallel=parallel,
        )

        if output:
            output = os.path.expanduser(output)
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
            with open(output, "w") as f:
                f.write(report)
            click.echo(f"Report written to: {output}", err=True)
        else:
            click.echo(report)

    except FileNotFoundError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        raise SystemExit(1)
    except RuntimeError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        raise SystemExit(1)
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.secho(f"Error: {e}", fg="red", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# eyeroll history
# ---------------------------------------------------------------------------

@cli.group(invoke_without_command=True)
@click.option("--limit", "-n", default=None, type=int,
              help="Show only the last N analyses.")
@click.option("--json", "as_json", is_flag=True,
              help="Output as JSON for programmatic use.")
@click.pass_context
def history(ctx, limit, as_json):
    """List and manage past video analyses from the cache.

    \b
    Without a subcommand, lists all cached analyses.
    Use 'eyeroll history clear' to remove cached data.
    """
    if ctx.invoked_subcommand is not None:
        return

    _print_history(limit, as_json)


def _print_history(limit, as_json):
    """Shared logic for printing history entries."""
    from .history import list_history

    entries = list_history(limit=limit)

    if as_json:
        click.echo(json.dumps(entries, indent=2))
        return

    if not entries:
        click.echo("No cached analyses found.")
        return

    for entry in entries:
        ts = entry.get("timestamp", "unknown")
        # Format ISO timestamp to readable form
        if ts != "unknown":
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ts)
                ts = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass

        source = entry.get("source", "unknown")
        key = entry.get("key", "?")
        media_type = entry.get("media_type", "")

        if media_type:
            click.echo(f"[{ts}] {source} ({media_type}) -- {key}")
        else:
            click.echo(f"[{ts}] {source} -- {key}")


@history.command(name="clear")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def history_clear(yes):
    """Clear all cached analyses."""
    from .history import clear_history, list_history

    entries = list_history()
    if not entries:
        click.echo("Cache is already empty.")
        return

    if not yes:
        if not click.confirm(f"Delete {len(entries)} cached analysis(es)?", default=False):
            click.echo("Aborted.")
            return

    clear_history()
    click.secho(f"Cleared {len(entries)} cached analysis(es).", fg="green")
