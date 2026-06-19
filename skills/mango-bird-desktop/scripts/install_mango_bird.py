#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def copy_app(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=True)


def write_env_template(config_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    template = config_dir / ".env.example"
    if not template.exists():
        template.write_text(
            "# Copy to .env and replace the placeholders with your own model service settings.\n"
            "# Supported providers: deepseek, glm.\n"
            "MANGO_AI_PROVIDER=deepseek\n"
            "MANGO_AI_API_KEY=sk-your-own-api-key\n",
            encoding="utf-8",
        )


def write_env(config_dir: Path, provider: str, api_key: str) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    env_file = config_dir / ".env"
    env_file.write_text(
        f"MANGO_AI_PROVIDER={provider.strip()}\n"
        f"MANGO_AI_API_KEY={api_key.strip()}\n",
        encoding="utf-8",
    )
    env_file.chmod(stat.S_IRUSR | stat.S_IWUSR)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and install Mango Bird for macOS.")
    parser.add_argument(
        "--install-dir",
        default=str(Path.home() / "Applications"),
        help="Directory where mango-bird.app will be copied. Defaults to ~/Applications.",
    )
    parser.add_argument(
        "--provider",
        choices=["deepseek", "glm"],
        default="deepseek",
        help="Model service provider to configure. Defaults to deepseek.",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Optional model service API key to write into the user-local .env file.",
    )
    parser.add_argument(
        "--deepseek-api-key",
        default="",
        help="Deprecated alias for --api-key --provider deepseek.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Copy the existing dist/mango-bird.app without rebuilding.",
    )
    parser.add_argument(
        "--config-dir",
        default=str(Path.home() / "Library" / "Application Support" / "Mango Bird"),
        help="Directory for the user-local .env files. Defaults to the Mango Bird Application Support folder.",
    )
    args = parser.parse_args()

    root = project_root()
    build_script = root / "macos" / "build-mango-bird-app.sh"
    app_source = root / "dist" / "mango-bird.app"
    app_destination = Path(args.install_dir).expanduser() / "mango-bird.app"
    config_dir = Path(args.config_dir).expanduser()

    if not args.skip_build:
        subprocess.run(["bash", str(build_script)], cwd=root, check=True)

    if not app_source.exists():
        raise SystemExit(f"App bundle not found: {app_source}")

    copy_app(app_source, app_destination)
    write_env_template(config_dir)
    api_key = args.api_key or args.deepseek_api_key
    provider = "deepseek" if args.deepseek_api_key and not args.api_key else args.provider
    if api_key:
        write_env(config_dir, provider, api_key)

    print(f"Installed app: {app_destination}")
    print(f"Config folder: {config_dir}")
    if api_key:
        print(f"{provider} API key saved to the user-local .env file.")
    else:
        print("To enable chat, enter an API key in the Mango Bird chat panel or edit .env in the config folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
