"""
DSA AutoGrader - Archive Handler.

Extract Python files from RAR/ZIP archives for grading.
Supports multiple backends with automatic fallback:
  - ZIP: Python built-in zipfile (always available)
  - RAR: patool → rarfile → pyunpack (tried in order)
"""

import logging
import os
import tempfile
from pathlib import PurePosixPath
from typing import List, Tuple

logger = logging.getLogger("dsa.archive")

# Security: Maximum archive size to prevent zip bombs (50MB)
MAX_ARCHIVE_SIZE = 50 * 1024 * 1024
MAX_EXTRACTED_FILES = 200
MAX_EXTRACTED_CODE_BYTES = 8 * 1024 * 1024


def _is_safe_archive_path(member_name: str) -> bool:
    """Reject absolute paths and traversal attempts inside archives."""
    if not member_name:
        return False

    normalized = member_name.replace("\\", "/")
    pure_path = PurePosixPath(normalized)

    if pure_path.is_absolute():
        return False

    if any(part == ".." for part in pure_path.parts):
        return False

    return True


def _safe_join(base_dir: str, member_name: str) -> str:
    """Join archive member path safely under the extraction root."""
    normalized = member_name.replace("\\", "/")
    target_path = os.path.abspath(os.path.join(base_dir, normalized))
    base_path = os.path.abspath(base_dir)
    if os.path.commonpath([base_path, target_path]) != base_path:
        raise ValueError(f"Unsafe archive path detected: {member_name}")
    return target_path


# ---------------------------------------------------------------------------
#  Helper: Collect .py files from a directory tree
# ---------------------------------------------------------------------------
def _collect_python_files(extract_dir: str) -> List[Tuple[str, str]]:
    """
    Walk the extracted directory and collect all Python files.

    Args:
        extract_dir: Root directory to search for .py files

    Returns:
        List of (relative_path, code_content) tuples
    """
    extracted_files = []
    total_code_bytes = 0

    for root, _, files in os.walk(extract_dir):
        for fname in files:
            if not fname.lower().endswith(".py"):
                continue

            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, extract_dir)

            # Try multiple encodings
            code = None
            for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                try:
                    with open(full_path, "r", encoding=encoding) as f:
                        code = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue

            if code is None:
                # Last resort: read as binary and decode with errors='replace'
                with open(full_path, "rb") as f:
                    code = f.read().decode("utf-8", errors="replace")

            extracted_files.append((rel_path, code))
            total_code_bytes += len(code.encode("utf-8", errors="ignore"))

            if len(extracted_files) > MAX_EXTRACTED_FILES:
                raise ValueError(
                    f"Archive contains too many Python files (> {MAX_EXTRACTED_FILES})"
                )
            if total_code_bytes > MAX_EXTRACTED_CODE_BYTES:
                max_mb = MAX_EXTRACTED_CODE_BYTES / (1024 * 1024)
                raise ValueError(
                    f"Extracted Python code exceeds safety limit ({max_mb:.0f}MB)"
                )

            logger.info("Collected Python file: %s (%d bytes)", rel_path, len(code))

    return extracted_files


# ---------------------------------------------------------------------------
#  RAR Backend 1: patool (no external tools required on most systems)
# ---------------------------------------------------------------------------
def _extract_rar_with_patool(
    archive_data: bytes, filename: str, temp_dir: str
) -> List[Tuple[str, str]]:
    """Extract RAR archive using patool."""
    raise ImportError("patool backend disabled for safe archive extraction")


# ---------------------------------------------------------------------------
#  RAR Backend 2: rarfile (requires unrar/WinRAR on system)
# ---------------------------------------------------------------------------
def _extract_rar_with_rarfile(
    archive_data: bytes, filename: str, temp_dir: str
) -> List[Tuple[str, str]]:
    """Extract RAR archive using rarfile module."""
    try:
        import rarfile
    except ImportError:
        raise ImportError("rarfile is not installed")

    archive_path = os.path.join(temp_dir, filename)
    with open(archive_path, "wb") as f:
        f.write(archive_data)

    extract_dir = os.path.join(temp_dir, "rarfile_out")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        with rarfile.RarFile(archive_path, "r") as rf:
            members = rf.infolist()
            unsafe_members = [
                getattr(member, "filename", "")
                for member in members
                if not _is_safe_archive_path(getattr(member, "filename", ""))
            ]
            if unsafe_members:
                raise ValueError(
                    "RAR archive contains unsafe paths: " + ", ".join(unsafe_members[:5])
                )

            for member in members:
                member_name = getattr(member, "filename", "")
                if not member_name.lower().endswith(".py"):
                    continue
                target_path = _safe_join(extract_dir, member_name)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with rf.open(member) as source, open(target_path, "wb") as target:
                    target.write(source.read())
    except rarfile.BadRarFile:
        raise ValueError("File is not a valid RAR archive or is corrupted")
    except rarfile.NeedFirstVolume:
        raise ValueError("Multi-volume RAR archives are not supported")
    except Exception as e:
        if "Unrar not installed" in str(e) or "unrar" in str(e).lower():
            raise ImportError(f"unrar tool not found: {e}")
        raise ValueError(f"rarfile extraction error: {e}")

    return _collect_python_files(extract_dir)


# ---------------------------------------------------------------------------
#  RAR Backend 3: pyunpack (another fallback)
# ---------------------------------------------------------------------------
def _extract_rar_with_pyunpack(
    archive_data: bytes, filename: str, temp_dir: str
) -> List[Tuple[str, str]]:
    """Extract RAR archive using pyunpack."""
    raise ImportError("pyunpack backend disabled for safe archive extraction")


# ---------------------------------------------------------------------------
#  Public API: extract_rar_file
# ---------------------------------------------------------------------------
def extract_rar_file(rar_data: bytes, filename: str) -> List[Tuple[str, str]]:
    """
    Extract Python files from a RAR archive.

    Tries multiple backends in order:
      1. patool   — works on most systems without WinRAR
      2. rarfile  — requires unrar or WinRAR
      3. pyunpack — another fallback

    Args:
        rar_data: Raw bytes of the RAR file
        filename: Original filename

    Returns:
        List of tuples (python_filename, python_code)

    Raises:
        ValueError: If no Python files found or extraction fails
    """
    backends = [
        ("patool", _extract_rar_with_patool),
        ("rarfile", _extract_rar_with_rarfile),
        ("pyunpack", _extract_rar_with_pyunpack),
    ]

    last_error = None

    for backend_name, extract_fn in backends:
        try:
            logger.info("Trying RAR extraction with %s...", backend_name)

            with tempfile.TemporaryDirectory() as temp_dir:
                extracted_files = extract_fn(rar_data, filename, temp_dir)

            if extracted_files:
                logger.info(
                    "RAR extracted successfully with %s: %d Python file(s)",
                    backend_name,
                    len(extracted_files),
                )
                return extracted_files
            else:
                logger.warning(
                    "%s extracted archive but found no .py files", backend_name
                )

        except ImportError as e:
            logger.info("%s not available: %s", backend_name, e)
            last_error = e
            continue
        except ValueError as e:
            logger.warning("%s failed: %s", backend_name, e)
            last_error = e
            continue
        except Exception as e:
            logger.warning("%s unexpected error: %s", backend_name, e)
            last_error = e
            continue

    # All backends failed
    if last_error:
        raise ValueError(
            f"Failed to extract RAR file '{filename}'. "
            f"Last error: {last_error}. "
            "Please ensure the RAR file is valid and contains .py files, "
            "or try uploading as a ZIP file instead."
        )
    else:
        raise ValueError(
            "No RAR extraction backend available. "
            "Please install patool (pip install patool) "
            "or upload as ZIP format instead."
        )


# ---------------------------------------------------------------------------
#  Public API: extract_zip_file
# ---------------------------------------------------------------------------
def extract_zip_file(zip_data: bytes, filename: str) -> List[Tuple[str, str]]:
    """
    Extract Python files from a ZIP archive.

    Args:
        zip_data: Raw bytes of the ZIP file
        filename: Original filename

    Returns:
        List of tuples (python_filename, python_code)

    Raises:
        ValueError: If no Python files found or extraction fails
    """
    import zipfile

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, filename)

        with open(zip_path, "wb") as f:
            f.write(zip_data)

        extract_dir = os.path.join(temp_dir, "zip_out")
        os.makedirs(extract_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for member in zf.infolist():
                    member_name = member.filename
                    if not _is_safe_archive_path(member_name):
                        raise ValueError(f"Unsafe archive path detected: {member_name}")
                    if member.is_dir():
                        continue
                    if not member_name.lower().endswith(".py"):
                        continue

                    target_path = _safe_join(extract_dir, member_name)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with zf.open(member, "r") as source, open(target_path, "wb") as target:
                        target.write(source.read())
        except zipfile.BadZipFile:
            raise ValueError("File is not a valid ZIP archive or is corrupted")
        except Exception as e:
            raise ValueError(f"Failed to extract ZIP: {e}")

        # Collect all .py files from extracted content
        extracted_files = _collect_python_files(extract_dir)

    if not extracted_files:
        raise ValueError("No Python (.py) files found in the ZIP archive")

    logger.info(
        "Extracted %d Python file(s) from ZIP: %s",
        len(extracted_files),
        filename,
    )
    return extracted_files


# ---------------------------------------------------------------------------
#  Public API: Utilities
# ---------------------------------------------------------------------------
def is_archive_file(filename: str) -> bool:
    """Check if filename is a supported archive format."""
    if not filename:
        return False
    return filename.lower().endswith((".rar", ".zip"))


def extract_archive(archive_data: bytes, filename: str) -> List[Tuple[str, str]]:
    """
    Extract Python files from an archive (RAR or ZIP).

    Security: Rejects archives larger than 50MB to prevent zip bombs.

    Args:
        archive_data: Raw bytes of the archive file
        filename: Original filename

    Returns:
        List of tuples (python_filename, python_code)

    Raises:
        ValueError: If archive format not supported, too large, or extraction fails
    """
    if not filename:
        raise ValueError("Filename is required")

    # Security check: reject oversized archives
    if len(archive_data) > MAX_ARCHIVE_SIZE:
        size_mb = len(archive_data) / (1024 * 1024)
        max_mb = MAX_ARCHIVE_SIZE / (1024 * 1024)
        raise ValueError(
            f"Archive too large: {size_mb:.1f}MB exceeds limit of {max_mb:.0f}MB"
        )

    filename_lower = filename.lower()

    if filename_lower.endswith(".rar"):
        return extract_rar_file(archive_data, filename)
    elif filename_lower.endswith(".zip"):
        return extract_zip_file(archive_data, filename)
    else:
        raise ValueError(
            f"Unsupported archive format: {filename}. " "Supported formats: .rar, .zip"
        )
