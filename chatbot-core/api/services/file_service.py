"""
File service layer responsible for processing uploaded files.

Handles extraction of text content from various file types including:
- Text files (.txt, .log, .md, .json, .xml, .yaml, .yml)
- Code files (.py, .js, .ts, .java, .groovy, etc.)
- Images (using base64 encoding for LLM vision models)
"""

import base64
import mimetypes
from typing import Tuple
from pathlib import Path
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")

# Supported text-based file extensions
TEXT_EXTENSIONS = {
    ".txt", ".log", ".md", ".json", ".xml", ".yaml", ".yml",
    ".py", ".js", ".ts", ".tsx", ".java", ".groovy", ".sh",
    ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".csv", ".html",
    ".css", ".scss", ".less", ".sql", ".rb", ".go", ".rs",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".swift", ".kt",
    ".jenkinsfile", ".dockerfile", ".properties", ".ini", ".cfg",
    ".conf", ".toml", ".gradle", ".pom", ".env", ".gitignore",
    ".dockerignore", ".editorconfig", ".eslintrc", ".prettierrc"
}

# Supported image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

# Maximum file size in bytes (5 MB for text, 10 MB for images)
MAX_TEXT_FILE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_FILE_SIZE = 10 * 1024 * 1024

# Maximum text content length to include in context
MAX_TEXT_CONTENT_LENGTH = 10000


class FileProcessingError(Exception):
    """Custom exception for file processing errors."""


def get_file_extension(filename: str) -> str:
    """
    Extracts the file extension from a filename.

    Args:
        filename: The name of the file.

    Returns:
        str: The lowercase file extension including the dot (e.g., ".txt").
    """
    return Path(filename).suffix.lower()


def is_text_file(filename: str) -> bool:
    """
    Checks if a file is a supported text-based file.

    Args:
        filename: The name of the file.

    Returns:
        bool: True if the file is a text-based file, False otherwise.
    """
    ext = get_file_extension(filename)
    base_name = Path(filename).name.lower()

    # Known text files without extension
    known_text_files = {
        "jenkinsfile", "dockerfile", "makefile", "readme", "license",
        ".env", ".gitignore", ".dockerignore", ".editorconfig",
        ".eslintrc", ".prettierrc", ".babelrc", ".npmrc"
    }

    # Check if extension is supported or if it's a known text file
    if ext in TEXT_EXTENSIONS:
        return True

    # Handle hidden files (starting with .)
    if base_name.startswith(".") and not ext:
        return True

    return base_name in known_text_files


def is_image_file(filename: str) -> bool:
    """
    Checks if a file is a supported image file.

    Args:
        filename: The name of the file.

    Returns:
        bool: True if the file is an image file, False otherwise.
    """
    return get_file_extension(filename) in IMAGE_EXTENSIONS


def is_supported_file(filename: str) -> bool:
    """
    Checks if a file type is supported for upload.

    Args:
        filename: The name of the file.

    Returns:
        bool: True if the file type is supported, False otherwise.
    """
    return is_text_file(filename) or is_image_file(filename)


def validate_file_size(content: bytes, filename: str) -> None:
    """
    Validates that a file doesn't exceed size limits.

    Args:
        content: The file content as bytes.
        filename: The name of the file.

    Raises:
        FileProcessingError: If the file exceeds size limits.
    """
    max_size = MAX_IMAGE_FILE_SIZE if is_image_file(filename) else MAX_TEXT_FILE_SIZE

    if len(content) > max_size:
        max_mb = max_size / (1024 * 1024)
        raise FileProcessingError(
            f"File '{filename}' exceeds maximum size of {max_mb:.1f} MB"
        )


def process_text_file(content: bytes, filename: str) -> str:
    """
    Processes a text file and extracts its content.

    Args:
        content: The file content as bytes.
        filename: The name of the file.

    Returns:
        str: The extracted text content, truncated if necessary.

    Raises:
        FileProcessingError: If the file cannot be decoded.
    """
    # Try common encodings
    encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]

    text_content = None
    for encoding in encodings:
        try:
            text_content = content.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text_content is None:
        raise FileProcessingError(
            f"Could not decode file '{filename}'. Unsupported encoding."
        )

    # Truncate if too long
    if len(text_content) > MAX_TEXT_CONTENT_LENGTH:
        logger.warning(
            "File '%s' content truncated from %d to %d characters",
            filename, len(text_content), MAX_TEXT_CONTENT_LENGTH
        )
        text_content = text_content[:MAX_TEXT_CONTENT_LENGTH] + "\n... [truncated]"

    return text_content


def process_image_file(content: bytes, filename: str) -> Tuple[str, str]:
    """
    Processes an image file and returns base64 encoding.

    Args:
        content: The file content as bytes.
        filename: The name of the file.

    Returns:
        Tuple[str, str]: A tuple of (base64_encoded_content, mime_type).
    """
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        ext = get_file_extension(filename)
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp"
        }
        mime_type = mime_map.get(ext, "application/octet-stream")

    base64_content = base64.b64encode(content).decode("utf-8")

    return base64_content, mime_type


def process_uploaded_file(content: bytes, filename: str) -> dict:
    """
    Processes an uploaded file and extracts relevant information.

    Args:
        content: The file content as bytes.
        filename: The name of the file.

    Returns:
        dict: A dictionary containing processed file information:
            - filename: Original filename
            - type: "text" or "image"
            - content: Text content or base64 encoded image
            - mime_type: MIME type (for images)

    Raises:
        FileProcessingError: If the file type is not supported or processing fails.
    """
    logger.info("Processing uploaded file: %s (%d bytes)", filename, len(content))

    if not is_supported_file(filename):
        raise FileProcessingError(
            f"Unsupported file type for '{filename}'. "
            f"Supported types: text files, code files, and images."
        )

    validate_file_size(content, filename)

    if is_text_file(filename):
        text_content = process_text_file(content, filename)
        return {
            "filename": filename,
            "type": "text",
            "content": text_content,
            "mime_type": "text/plain"
        }

    if is_image_file(filename):
        base64_content, mime_type = process_image_file(content, filename)
        return {
            "filename": filename,
            "type": "image",
            "content": base64_content,
            "mime_type": mime_type
        }

    # Should not reach here due to is_supported_file check
    raise FileProcessingError(f"Unknown file type for '{filename}'")


def format_file_context(processed_files: list) -> str:
    """
    Formats processed files into context string for the LLM.

    Uses XML-style tags as robust separators that won't conflict with
    markdown content containing triple backticks.

    Args:
        processed_files: List of processed file dictionaries.

    Returns:
        str: Formatted context string containing file contents.
    """
    if not processed_files:
        return ""

    context_parts = []

    for file_info in processed_files:
        filename = file_info.get("filename", "unknown")
        file_type = file_info.get("type", "unknown")
        content = file_info.get("content", "")

        if file_type == "text":
            # Use XML-style tags as robust separators to avoid conflicts
            # with markdown content that may contain triple backticks
            context_parts.append(
                f"<uploaded_file name=\"{filename}\">\n"
                f"{content}\n"
                f"</uploaded_file>"
            )
        elif file_type == "image":
            # For images, we note their presence; actual image processing
            # would require vision-capable LLM
            context_parts.append(
                f"<uploaded_image name=\"{filename}\">\n"
                f"(Image content available for vision-capable models)\n"
                f"</uploaded_image>"
            )

    return "\n\n".join(context_parts)


def get_supported_extensions() -> dict:
    """
    Returns information about supported file extensions.

    Returns:
        dict: Dictionary with 'text' and 'image' keys containing lists of extensions.
    """
    return {
        "text": sorted(TEXT_EXTENSIONS),
        "image": sorted(IMAGE_EXTENSIONS),
        "max_text_size_mb": MAX_TEXT_FILE_SIZE / (1024 * 1024),
        "max_image_size_mb": MAX_IMAGE_FILE_SIZE / (1024 * 1024)
    }
