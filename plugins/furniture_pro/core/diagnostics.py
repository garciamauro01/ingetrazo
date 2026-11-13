# SPDX-License-Identifier: GPL-3.0-or-later
"""Self-diagnosis report shown by Extensions ▸ Furniture Pro ▸ Diagnostics.

The report is intentionally plain text: users paste it into a support message
and it must not depend on Qt or on the host being fully initialised.
"""
from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from .constants import PLUGIN_NAME, PLUGIN_VERSION, SCHEMA_VERSION
from .logging_utils import get_logger, log_dir, user_data_dir


def environment_report(host=None, libraries: dict | None = None,
                       project=None) -> str:
    """Return a stable, human-readable diagnostic report."""
    lines = [
        f"{PLUGIN_NAME} {PLUGIN_VERSION}",
        f"Schema: {SCHEMA_VERSION}",
        f"Generated: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}",
        "",
        "Environment",
        f"- Python: {sys.version.split()[0]} ({platform.platform()})",
        f"- Executable: {sys.executable}",
        f"- User data: {user_data_dir()}",
        f"- Logs: {log_dir()}",
    ]
    try:
        import PySide6
        lines.append(f"- PySide6: {PySide6.__version__}")
    except Exception:                                   # noqa: BLE001
        lines.append("- PySide6: NOT AVAILABLE")
    try:
        from core.version import __version__ as host_version
        lines.append(f"- Ingetrazo source: {host_version}")
    except Exception:                                   # noqa: BLE001
        lines.append("- Ingetrazo source: not importable in this process")

    if host is not None:
        lines.extend([
            "",
            "Host API",
            f"- Extension key: {getattr(host, 'key', '?')}",
            f"- API version: {getattr(host, 'api_version', '?')}",
            f"- Viewport: {type(getattr(host, 'viewport', None)).__name__}",
        ])
    else:
        lines.extend(["", "Host API", "- Not running inside Ingetrazo."])

    if libraries:
        lines.extend(["", "Libraries"])
        for name, library in libraries.items():
            try:
                count = len(library)
            except TypeError:
                count = "?"
            lines.append(f"- {name}: {count} entries")

    if project is not None:
        try:
            modules = project.modules
            lines.extend([
                "", "Project",
                f"- Name: {project.name or '(sem nome)'}",
                f"- Modules: {len(modules)}",
                f"- Currency: {project.settings.currency}",
            ])
        except Exception:                               # noqa: BLE001
            lines.append("- Project data could not be summarised.")

    lines.extend([
        "",
        "Known limitations (MVP)",
        "- Hinge and drawer mounting dimensions are only emitted when the user",
        "  marks a hardware specification as verified; no manufacturer data is",
        "  invented.",
        "- DXF export is intentionally absent until a validated DXF library is",
        "  available. PDF, CSV and JSON exports are implemented.",
        "- The cutting plan uses MaxRects/BSSF; advanced nesting (common-line,",
        "  guillotine, remnant inventory) is future work.",
        "- Interactive GUI testing requires a running Ingetrazo session; the",
        "  automated tests exercise the domain layer offscreen.",
    ])
    return "\n".join(lines)


def log_diagnostic(report: str) -> None:
    get_logger().info("Diagnostic report requested:\n%s", report)
