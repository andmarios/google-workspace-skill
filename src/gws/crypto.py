"""Encryption at rest for secret files (tokens, credentials, API keys).

Derives a Fernet key at runtime from machine-specific identifiers so the key
is never stored on disk.  An attacker who exfiltrates encrypted files to
another machine (or another user account) cannot decrypt them.

Two modes:
- auto (default): key derived from machine_id + username + salt via HKDF
- none (opt-out via env var): no encryption, plaintext JSON
"""

import base64
import getpass
import json
import os
import platform
import secrets as secrets_mod
import subprocess
import sys
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# ---------------------------------------------------------------------------
# Machine fingerprint (cross-platform)
# ---------------------------------------------------------------------------

def _get_machine_id_linux() -> str:
    try:
        return Path("/etc/machine-id").read_text().strip()
    except (OSError, FileNotFoundError):
        return ""


def _get_machine_id_macos() -> str:
    try:
        result = subprocess.run(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "IOPlatformUUID" in line:
                # Line format: "IOPlatformUUID" = "XXXXXXXX-XXXX-..."
                parts = line.split('"')
                if len(parts) >= 4:
                    return parts[-2]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


def _get_machine_id_windows() -> str:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        )
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return str(value)
    except (OSError, ImportError):
        return ""


def get_machine_id() -> str:
    """Get a stable, per-installation machine identifier."""
    system = platform.system()
    if system == "Linux":
        return _get_machine_id_linux()
    elif system == "Darwin":
        return _get_machine_id_macos()
    elif system == "Windows":
        return _get_machine_id_windows()
    return ""


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

def generate_salt() -> str:
    """Generate a random 64-char hex salt for key derivation."""
    return secrets_mod.token_hex(32)


def derive_key(salt: str, app_id: str) -> bytes:
    """Derive a Fernet key from machine fingerprint + username + salt.

    Args:
        salt: Random salt stored in the (plaintext) config file.
        app_id: Application identifier (e.g. "gws-cli" or "zd-cli").

    Returns:
        URL-safe base64-encoded 32-byte key suitable for Fernet.

    Raises:
        RuntimeError: If the machine ID cannot be determined.
    """
    machine_id = get_machine_id()
    if not machine_id:
        raise RuntimeError(
            "Cannot derive encryption key: machine ID not available. "
            "Set the appropriate *_ENCRYPTION=none env var to disable encryption."
        )

    username = getpass.getuser()
    fingerprint = f"{machine_id}:{username}:{app_id}".encode()

    hkdf = HKDF(
        algorithm=SHA256(),
        length=32,
        salt=salt.encode(),
        info=b"token-encryption",
    )
    key_bytes = hkdf.derive(fingerprint)
    return base64.urlsafe_b64encode(key_bytes)


# ---------------------------------------------------------------------------
# Encrypt / decrypt helpers
# ---------------------------------------------------------------------------

def _enc_path(path: Path) -> Path:
    """Return the .enc sibling of a path: token.json → token.json.enc."""
    return path.parent / (path.name + ".enc")


def save_encrypted(path: Path, data: dict[str, Any], key: bytes | None) -> None:
    """Save *data* as JSON — encrypted if *key* is provided, plaintext otherwise.

    Encrypted files are written with the ``.enc`` suffix appended to *path*.
    If a plaintext version of the file exists when saving encrypted, it is
    removed (migration cleanup).  Files are created with 0o600 permissions.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if key is not None:
        dest = _enc_path(path)
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(json.dumps(data, indent=2).encode())
        fd = os.open(str(dest), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(ciphertext)
        # Remove plaintext leftover from before encryption was enabled
        if path.exists():
            path.unlink()
    else:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)


def load_encrypted(path: Path, key: bytes | None) -> dict[str, Any] | None:
    """Load a JSON dict, handling both encrypted and plaintext files.

    When *key* is provided:
      1. Try ``path.enc`` first — decrypt and return.
      2. Fall back to plaintext *path* — auto-migrate (encrypt in place) and return.
      3. If decryption fails (key changed / wrong machine): return ``None``.

    When *key* is ``None``: read plaintext *path* only.

    Returns ``None`` if the file does not exist or cannot be read.
    """
    enc = _enc_path(path)

    if key is not None:
        # Prefer encrypted file
        if enc.exists():
            try:
                ciphertext = enc.read_bytes()
                plaintext = Fernet(key).decrypt(ciphertext)
                return json.loads(plaintext)
            except (InvalidToken, json.JSONDecodeError):
                print(
                    f"[crypto] Warning: cannot decrypt {enc.name} "
                    "(machine changed?). Re-authentication required.",
                    file=sys.stderr,
                )
                return None

        # Fall back to plaintext and auto-migrate
        if path.exists():
            try:
                with open(path) as f:
                    data: dict[str, Any] = json.load(f)
                save_encrypted(path, data, key)  # migrate
                return data
            except (json.JSONDecodeError, OSError):
                return None
    else:
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return None

    return None


def delete_encrypted(path: Path) -> bool:
    """Delete both encrypted (``.enc``) and plaintext versions of a file."""
    deleted = False
    enc = _enc_path(path)
    if enc.exists():
        enc.unlink()
        deleted = True
    if path.exists():
        path.unlink()
        deleted = True
    return deleted
