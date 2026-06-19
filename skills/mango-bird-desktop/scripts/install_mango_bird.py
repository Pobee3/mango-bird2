#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional


DEFAULT_REPO_URL = "https://github.com/Pobee3/mango-bird2.git"
DEFAULT_APP_ZIP_URL = "https://github.com/Pobee3/mango-bird2/releases/latest/download/mango-bird.zip"
REQUIRED_PROJECT_FILES = (
    "mango-bird.html",
    "mango-bird-server.py",
    "macos/build-mango-bird-app.sh",
)
REQUIRED_RUNTIME_ASSETS = (
    "assets/芒果_nobg.png",
    "assets/终图_绿翅.png",
    "new2/左边走.png",
)


def is_project_root(path: Path) -> bool:
    return all((path / file_name).exists() for file_name in REQUIRED_PROJECT_FILES)


def has_runtime_assets(path: Path) -> bool:
    return all((path / file_name).exists() for file_name in REQUIRED_RUNTIME_ASSETS)


def find_project_root(start: Path) -> Optional[Path]:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if is_project_root(candidate):
            return candidate
    return None


def default_checkout_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "Mango Bird" / "source"


def clone_project(repo_url: str, checkout_dir: Path) -> Path:
    if checkout_dir.exists():
        if is_project_root(checkout_dir):
            return checkout_dir
        if any(checkout_dir.iterdir()):
            raise SystemExit(
                f"Checkout directory exists but is not a Mango Bird project: {checkout_dir}"
            )
    checkout_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", repo_url, str(checkout_dir)], check=True)
    if not is_project_root(checkout_dir):
        raise SystemExit(f"Downloaded repository is missing Mango Bird files: {checkout_dir}")
    return checkout_dir


def update_project(root: Path) -> None:
    if (root / ".git").exists():
        subprocess.run(["git", "-C", str(root), "pull", "--ff-only"], check=True)


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response:
        with destination.open("wb") as output:
            shutil.copyfileobj(response, output)


def extract_app_from_zip(zip_path: Path, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)
    apps = sorted(
        candidate
        for candidate in destination.rglob("*.app")
        if "__MACOSX" not in candidate.parts
        and not candidate.name.startswith("._")
        and (candidate / "Contents" / "Info.plist").exists()
        and any((candidate / "Contents" / "MacOS").glob("*"))
    )
    if not apps:
        raise SystemExit(f"No valid .app bundle found in downloaded ZIP: {zip_path}")
    return apps[0]


def download_app(app_zip_url: str) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="mango-bird-install-"))
    zip_path = temp_dir / "mango-bird.zip"
    extract_dir = temp_dir / "app"
    print(f"Downloading Mango Bird app from: {app_zip_url}")
    download_file(app_zip_url, zip_path)
    return extract_app_from_zip(zip_path, extract_dir)


def project_root(args: argparse.Namespace) -> Path:
    if args.source_dir:
        root = Path(args.source_dir).expanduser()
        if not is_project_root(root):
            raise SystemExit(f"Not a Mango Bird project root: {root}")
        return root

    bundled_root = find_project_root(Path(__file__))
    if bundled_root:
        if args.update_source:
            update_project(bundled_root)
        return bundled_root

    repo_url = args.repo_url or os.environ.get("MANGO_BIRD_REPO_URL") or DEFAULT_REPO_URL
    checkout_dir = Path(args.checkout_dir).expanduser()
    root = clone_project(repo_url, checkout_dir)
    if args.update_source:
        update_project(root)
    return root


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
            "MANGO_AI_API_KEY=your-api-key\n",
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
        "--repo-url",
        default="",
        help=f"Git repository to clone when --build-from-source is used. Defaults to {DEFAULT_REPO_URL}.",
    )
    parser.add_argument(
        "--app-zip-url",
        default=DEFAULT_APP_ZIP_URL,
        help=f"Prebuilt app ZIP to download for normal installs. Defaults to {DEFAULT_APP_ZIP_URL}.",
    )
    parser.add_argument(
        "--checkout-dir",
        default=str(default_checkout_dir()),
        help="Where to clone the project when --build-from-source is used.",
    )
    parser.add_argument(
        "--source-dir",
        default="",
        help="Existing Mango Bird project root to build from. Overrides --repo-url.",
    )
    parser.add_argument(
        "--update-source",
        action="store_true",
        help="Run git pull --ff-only before building when the source is a git checkout.",
    )
    parser.add_argument(
        "--build-from-source",
        action="store_true",
        help="Build from a local or cloned source checkout instead of downloading the release app ZIP.",
    )
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

    if platform.system() != "Darwin":
        raise SystemExit("Mango Bird desktop app is macOS-only.")

    app_destination = Path(args.install_dir).expanduser() / "mango-bird.app"
    config_dir = Path(args.config_dir).expanduser()

    bundled_root = find_project_root(Path(__file__))
    should_build = (
        args.build_from_source
        or args.source_dir
        or (bundled_root and not args.skip_build and has_runtime_assets(bundled_root))
    )
    if should_build:
        root = project_root(args)
        build_script = root / "macos" / "build-mango-bird-app.sh"
        app_source = root / "dist" / "mango-bird.app"
        if not args.skip_build:
            subprocess.run(["bash", str(build_script)], cwd=root, check=True)
    elif args.skip_build:
        root = project_root(args)
        app_source = root / "dist" / "mango-bird.app"
    else:
        app_source = download_app(args.app_zip_url)

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
