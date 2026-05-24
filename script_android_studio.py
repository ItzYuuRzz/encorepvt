#!/usr/bin/env python3
"""
Standalone Google One offer-link runner for an Android Studio emulator/device.

This bypasses Firebase Test Lab, Firestore, Telegram, and Device Manager. It only
connects to a local Android device through Appium and runs GoogleOneAutomation.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent
DEVICE_AUTOMATION_DIR = REPO_ROOT / "services" / "device_automation"
sys.path.insert(0, str(DEVICE_AUTOMATION_DIR))

DEFAULT_APPIUM_SERVER = "http://127.0.0.1:4723"
GOOGLE_ONE_PACKAGE = "com.google.android.apps.subscriptions.red"


def run_adb(args: Iterable[str], *, udid: str | None = None) -> subprocess.CompletedProcess[str]:
    command = ["adb"]
    if udid:
        command.extend(["-s", udid])
    command.extend(args)
    return subprocess.run(command, text=True, capture_output=True, check=False)


def get_connected_devices() -> list[str]:
    result = run_adb(["devices"])
    if result.returncode != 0:
        raise RuntimeError(f"adb devices failed: {result.stderr.strip() or result.stdout.strip()}")

    devices: list[str] = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def choose_udid(requested_udid: str | None) -> str:
    devices = get_connected_devices()
    if requested_udid:
        if requested_udid not in devices:
            raise RuntimeError(
                f"Device {requested_udid!r} not found. Connected devices: {devices or 'none'}"
            )
        return requested_udid

    if not devices:
        raise RuntimeError(
            "No Android device/emulator found. Start an Android Studio emulator first, "
            "then check `adb devices`."
        )

    if len(devices) > 1:
        print(f"Multiple devices detected, using first: {devices[0]}", file=sys.stderr)
        print(f"Use --udid to choose explicitly. Devices: {', '.join(devices)}", file=sys.stderr)

    return devices[0]


def ensure_google_one_installed(udid: str) -> None:
    result = run_adb(["shell", "pm", "list", "packages", GOOGLE_ONE_PACKAGE], udid=udid)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to check installed packages: {result.stderr.strip()}")
    if f"package:{GOOGLE_ONE_PACKAGE}" not in result.stdout:
        raise RuntimeError(
            f"Google One is not installed on {udid}. Install it first, then rerun this script.\n"
            f"Expected package: {GOOGLE_ONE_PACKAGE}"
        )


def create_driver(server_url: str, udid: str, device_name: str):
    from appium import webdriver
    from appium.options.android import UiAutomator2Options

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.device_name = device_name
    options.udid = udid
    options.no_reset = True
    options.full_reset = False
    options.auto_grant_permissions = True
    options.new_command_timeout = 300
    return webdriver.Remote(server_url, options=options)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run GoogleOneAutomation on a local Android Studio emulator/device "
            "instead of Firebase Test Lab."
        )
    )
    parser.add_argument(
        "--appium-server",
        default=DEFAULT_APPIUM_SERVER,
        help=f"Appium server URL. Default: {DEFAULT_APPIUM_SERVER}",
    )
    parser.add_argument(
        "--udid",
        help="ADB device/emulator id. If omitted, the first `adb devices` entry is used.",
    )
    parser.add_argument(
        "--device-name",
        default="Android Emulator",
        help="Appium deviceName capability. Default: Android Emulator",
    )
    parser.add_argument(
        "--skip-install-check",
        action="store_true",
        help="Skip the ADB check for the Google One package before starting Appium.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        udid = choose_udid(args.udid)
        if not args.skip_install_check:
            ensure_google_one_installed(udid)

        print(f"Using device: {udid}")
        print(f"Connecting to Appium: {args.appium_server}")

        driver = create_driver(args.appium_server, udid, args.device_name)
    except Exception as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        return 1

    try:
        from google_one_automation import GoogleOneAutomation

        automation = GoogleOneAutomation(driver)
        offer_link = automation.get_offer_link()
        print("\nOFFER LINK:")
        print(offer_link)
        return 0
    except Exception as exc:
        print(f"Google One automation failed: {exc}", file=sys.stderr)
        return 2
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
