"""CLI entry point for eyeroll."""

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
    """Set up your Gemini API key."""
    env_dir = os.path.dirname(_ENV_PATH)
    os.makedirs(env_dir, exist_ok=True)

    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH) as f:
            if "GEMINI_API_KEY=" in f.read():
                if not click.confirm("API key already configured. Overwrite?", default=False):
                    return

    api_key = click.prompt(
        "Enter your Gemini API key\n"
        "  Get one at https://aistudio.google.com/apikey\n"
        "  (input is hidden)",
        hide_input=True,
    )

    with open(_ENV_PATH, "w") as f:
        f.write(f"GEMINI_API_KEY={api_key}\n")

    os.environ["GEMINI_API_KEY"] = api_key
    click.echo("Validating API key...")

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say 'ok' if you can read this.",
        )
        if response.text:
            click.secho("Setup complete. Run `eyeroll watch <video>` to get started.", fg="green")
        else:
            click.secho("API key accepted but got empty response.", fg="yellow")
    except Exception as e:
        click.secho(f"Validation failed: {e}", fg="red", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("source")
@click.option("--context", "-c", default=None,
              help="Additional context (Slack message, issue description, what to do with the video, etc.)")
@click.option("--max-frames", default=20, show_default=True,
              help="Maximum key frames to analyze from video.")
@click.option("--backend", "-b", type=click.Choice(["gemini", "ollama"]), default=None,
              help="Vision backend. Defaults to EYEROLL_BACKEND env var, then gemini.")
@click.option("--model", "-m", default=None,
              help="Model override (e.g., qwen3-vl:8b for ollama, gemini-2.0-flash for gemini).")
@click.option("--output", "-o", default=None,
              help="Write output to file instead of stdout.")
@click.option("--verbose", "-v", is_flag=True, help="Show progress details.")
def watch(source, context, max_frames, backend, model, output, verbose):
    """Analyze a video/screenshot and produce structured notes.

    SOURCE can be a URL (YouTube, Loom, etc.) or a local file path.

    \b
    Backends:
      gemini   Google Gemini Flash API (default, requires GEMINI_API_KEY)
      ollama   Local models via Ollama (e.g., qwen3-vl, no API key needed)

    \b
    Examples:
      eyeroll watch https://loom.com/share/abc123
      eyeroll watch ./recording.mp4 --context "checkout broken after PR #432"
      eyeroll watch demo.mp4 -c "create a skill from this" --backend ollama
      eyeroll watch screenshot.png -b ollama -m qwen3-vl:2b
    """
    from .watch import watch as run_watch

    # --model without --backend implies ollama if model looks local
    if model and not backend:
        if not model.startswith("gemini"):
            backend = "ollama"

    try:
        report = run_watch(
            source=source,
            context=context,
            max_frames=max_frames,
            backend_name=backend,
            model=model,
            verbose=verbose,
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
