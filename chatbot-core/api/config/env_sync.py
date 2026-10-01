"""Synchronize provider API-key entries with the local environment file."""

import argparse
import re
from pathlib import Path
from collections.abc import Iterable

from api.config.providers import ProviderDefinition, load_provider_catalog

_CONFIG_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_PATH = _CONFIG_DIR.parent.parent / ".env"
_MANAGED_START = "# LiteLLM provider keys - managed"
_MANAGED_END = "# End LiteLLM provider keys"
_ENV_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")


def sync_provider_env(
    providers: Iterable[ProviderDefinition],
    env_path: Path = DEFAULT_ENV_PATH,
) -> None:
    """Synchronize managed provider API-key entries with an environment file.

    Args:
        providers (Iterable[ProviderDefinition]): Provider definitions to sync.
        env_path (Path): Environment file to update.
    """
    provider_list = [provider for provider in providers if provider.id != "local"]
    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    values = {
        match.group(1): match.group(2)
        for line in existing.splitlines()
        if (match := _ENV_LINE.match(line.strip()))
    }

    unmanaged_lines: list[str] = []
    in_managed_block = False
    managed_keys = {provider.api_key_env for provider in provider_list}
    for line in existing.splitlines():
        stripped = line.strip()
        if stripped == _MANAGED_START:
            in_managed_block = True
            continue
        if stripped == _MANAGED_END:
            in_managed_block = False
            continue
        if in_managed_block:
            continue
        match = _ENV_LINE.match(stripped)
        if match and match.group(1) in managed_keys:
            continue
        unmanaged_lines.append(line)

    while unmanaged_lines and not unmanaged_lines[-1].strip():
        unmanaged_lines.pop()

    managed_lines = [_MANAGED_START, ""]
    for provider in provider_list:
        managed_lines.extend(
            [
                f"# {provider.label}",
                f"{provider.api_key_env}={values.get(provider.api_key_env, '')}",
                "",
            ]
        )
    managed_lines.append(_MANAGED_END)

    output_lines = unmanaged_lines + ([""] if unmanaged_lines else []) + managed_lines
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")


def main() -> None:
    """Synchronize the provider catalog into the selected environment file."""
    parser = argparse.ArgumentParser(
        description="Synchronize provider API-key entries into a .env file."
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        help="Provider catalog path; defaults to api/config/providers.json.",
    )
    parser.add_argument(
        "--env",
        dest="env_path",
        type=Path,
        default=DEFAULT_ENV_PATH,
        help="Environment file path; defaults to chatbot-core/.env.",
    )
    args = parser.parse_args()
    providers = (
        load_provider_catalog(args.catalog)
        if args.catalog
        else load_provider_catalog()
    )
    sync_provider_env(providers, args.env_path)
    print(f"Synchronized {len(providers) - 1} hosted provider key entries.")


if __name__ == "__main__":
    main()
