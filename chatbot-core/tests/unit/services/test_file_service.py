"""Unit tests for file_service module."""

import base64
import pytest
from api.services.file_service import (
    get_file_extension,
    is_text_file,
    is_image_file,
    is_supported_file,
    validate_file_size,
    validate_file_content_type,
    detect_mime_type_from_content,
    process_text_file,
    process_image_file,
    process_uploaded_file,
    format_file_context,
    get_supported_extensions,
    FileProcessingError,
    MAX_TEXT_FILE_SIZE,
    MAX_IMAGE_FILE_SIZE,
    MAX_TEXT_CONTENT_LENGTH,
)


class TestGetFileExtension:
    """Tests for get_file_extension function."""

    def test_returns_lowercase_extension(self):
        """Test that extension is returned in lowercase."""
        assert get_file_extension("test.TXT") == ".txt"
        assert get_file_extension("file.JSON") == ".json"

    def test_handles_multiple_dots(self):
        """Test handling of filenames with multiple dots."""
        assert get_file_extension("test.config.yml") == ".yml"
        assert get_file_extension("my.file.name.py") == ".py"

    def test_returns_empty_for_no_extension(self):
        """Test that empty string is returned for files without extension."""
        assert get_file_extension("Jenkinsfile") == ""
        assert get_file_extension("Dockerfile") == ""


class TestIsTextFile:
    """Tests for is_text_file function."""

    def test_recognizes_text_extensions(self):
        """Test that common text extensions are recognized."""
        assert is_text_file("test.txt") is True
        assert is_text_file("log.log") is True
        assert is_text_file("readme.md") is True
        assert is_text_file("config.json") is True
        assert is_text_file("script.py") is True
        assert is_text_file("code.java") is True
        assert is_text_file("pipeline.groovy") is True

    def test_recognizes_known_text_files_without_extension(self):
        """Test that known filenames without extension are recognized."""
        assert is_text_file("Jenkinsfile") is True
        assert is_text_file("Dockerfile") is True
        assert is_text_file("Makefile") is True

    def test_recognizes_hidden_files(self):
        """Test that hidden files (dotfiles) are recognized as text files."""
        assert is_text_file(".env") is True
        assert is_text_file(".gitignore") is True
        assert is_text_file(".dockerignore") is True
        assert is_text_file(".editorconfig") is True
        assert is_text_file(".eslintrc") is True
        assert is_text_file(".prettierrc") is True
        assert is_text_file(".babelrc") is True
        assert is_text_file(".npmrc") is True

    def test_rejects_non_text_files(self):
        """Test that non-text files are rejected."""
        assert is_text_file("image.png") is False
        assert is_text_file("photo.jpg") is False
        assert is_text_file("archive.zip") is False


class TestIsImageFile:
    """Tests for is_image_file function."""

    def test_recognizes_image_extensions(self):
        """Test that common image extensions are recognized."""
        assert is_image_file("photo.png") is True
        assert is_image_file("image.jpg") is True
        assert is_image_file("picture.jpeg") is True
        assert is_image_file("animation.gif") is True
        assert is_image_file("modern.webp") is True

    def test_rejects_non_image_files(self):
        """Test that non-image files are rejected."""
        assert is_image_file("document.txt") is False
        assert is_image_file("script.py") is False


class TestIsSupportedFile:
    """Tests for is_supported_file function."""

    def test_supports_text_files(self):
        """Test that text files are supported."""
        assert is_supported_file("test.txt") is True
        assert is_supported_file("code.py") is True

    def test_supports_image_files(self):
        """Test that image files are supported."""
        assert is_supported_file("photo.png") is True
        assert is_supported_file("image.jpg") is True

    def test_rejects_unsupported_files(self):
        """Test that unsupported files are rejected."""
        assert is_supported_file("archive.zip") is False
        assert is_supported_file("document.pdf") is False


class TestValidateFileSize:
    """Tests for validate_file_size function."""

    def test_accepts_small_text_file(self):
        """Test that small text files are accepted."""
        content = b"Hello, World!"
        validate_file_size(content, "test.txt")  # Should not raise

    def test_accepts_small_image_file(self):
        """Test that small image files are accepted."""
        content = b"fake image data" * 1000
        validate_file_size(content, "photo.png")  # Should not raise

    def test_rejects_oversized_text_file(self):
        """Test that oversized text files are rejected."""
        content = b"x" * (MAX_TEXT_FILE_SIZE + 1)
        with pytest.raises(FileProcessingError) as exc_info:
            validate_file_size(content, "large.txt")
        assert "exceeds maximum size" in str(exc_info.value)

    def test_rejects_oversized_image_file(self):
        """Test that oversized image files are rejected."""
        content = b"x" * (MAX_IMAGE_FILE_SIZE + 1)
        with pytest.raises(FileProcessingError) as exc_info:
            validate_file_size(content, "large.png")
        assert "exceeds maximum size" in str(exc_info.value)


class TestDetectMimeTypeFromContent:
    """Tests for detect_mime_type_from_content function."""

    def test_detects_png(self):
        """Test PNG magic byte detection."""
        png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        result = detect_mime_type_from_content(png_header)
        assert result == 'image/png'

    def test_detects_jpeg(self):
        """Test JPEG magic byte detection."""
        jpeg_header = b'\xff\xd8\xff' + b'\x00' * 100
        result = detect_mime_type_from_content(jpeg_header)
        assert result == 'image/jpeg'

    def test_detects_gif(self):
        """Test GIF magic byte detection."""
        gif87_header = b'GIF87a' + b'\x00' * 100
        gif89_header = b'GIF89a' + b'\x00' * 100
        assert detect_mime_type_from_content(gif87_header) == 'image/gif'
        assert detect_mime_type_from_content(gif89_header) == 'image/gif'

    def test_detects_bmp(self):
        """Test BMP magic byte detection."""
        bmp_header = b'BM' + b'\x00' * 100
        result = detect_mime_type_from_content(bmp_header)
        assert result == 'image/bmp'

    def test_returns_none_for_unknown(self):
        """Test that None is returned for unknown content."""
        unknown_content = b'random binary data here'
        result = detect_mime_type_from_content(unknown_content)
        assert result is None

    def test_handles_empty_content(self):
        """Test that empty content returns None."""
        assert detect_mime_type_from_content(b'') is None
        assert detect_mime_type_from_content(None) is None


class TestValidateFileContentType:
    """Tests for validate_file_content_type function."""

    def test_accepts_valid_png(self):
        """Test that valid PNG passes validation."""
        png_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        validate_file_content_type(png_content, "test.png")  # Should not raise

    def test_accepts_valid_jpeg(self):
        """Test that valid JPEG passes validation."""
        jpeg_content = b'\xff\xd8\xff' + b'\x00' * 100
        validate_file_content_type(jpeg_content, "test.jpg")  # Should not raise

    def test_rejects_mismatched_image_extension(self):
        """Test that mismatched image content/extension is rejected."""
        png_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        with pytest.raises(FileProcessingError) as exc_info:
            validate_file_content_type(png_content, "fake.jpg")
        assert "content does not match" in str(exc_info.value)

    def test_accepts_text_file(self):
        """Test that text content passes validation."""
        text_content = b"print('Hello, World!')"
        validate_file_content_type(text_content, "script.py")  # Should not raise

    def test_accepts_valid_gif_extension(self):
        """Test that valid GIF passes validation."""
        gif_content = b'GIF89a' + b'\x00' * 100
        validate_file_content_type(gif_content, "animation.gif")  # Should not raise


class TestProcessTextFile:
    """Tests for process_text_file function."""

    def test_decodes_utf8_content(self):
        """Test that UTF-8 content is decoded correctly."""
        content = "Hello, World! こんにちは".encode("utf-8")
        result = process_text_file(content, "test.txt")
        assert "Hello, World!" in result
        assert "こんにちは" in result

    def test_decodes_latin1_content(self):
        """Test that Latin-1 content is decoded correctly."""
        content = "Héllo, Wörld!".encode("latin-1")
        result = process_text_file(content, "test.txt")
        assert "Héllo" in result

    def test_truncates_long_content(self):
        """Test that long content is truncated."""
        content = ("x" * (MAX_TEXT_CONTENT_LENGTH + 100)).encode("utf-8")
        result = process_text_file(content, "test.txt")
        assert len(result) <= MAX_TEXT_CONTENT_LENGTH + 50  # Allow for truncation marker
        assert "[truncated]" in result


class TestProcessImageFile:
    """Tests for process_image_file function."""

    def test_returns_base64_encoded_content(self):
        """Test that image content is base64 encoded."""
        content = b"fake image data"
        base64_content, _ = process_image_file(content, "test.png")

        # Verify it's valid base64
        decoded = base64.b64decode(base64_content)
        assert decoded == content

    def test_returns_correct_mime_type(self):
        """Test that correct MIME type is returned."""
        content = b"fake image data"

        _, mime_type = process_image_file(content, "test.png")
        assert mime_type == "image/png"

        _, mime_type = process_image_file(content, "test.jpg")
        assert mime_type == "image/jpeg"

        _, mime_type = process_image_file(content, "test.gif")
        assert mime_type == "image/gif"

    def test_rejects_unknown_image_extension(self):
        """Test that unknown image extensions are rejected instead of fallback."""
        content = b"fake image data"
        with pytest.raises(FileProcessingError) as exc_info:
            process_image_file(content, "image.unknown")
        assert "Cannot determine MIME type" in str(exc_info.value)


class TestProcessUploadedFile:
    """Tests for process_uploaded_file function."""

    def test_processes_text_file(self):
        """Test processing a text file."""
        content = b"print('Hello, World!')"
        result = process_uploaded_file(content, "script.py")

        assert result["filename"] == "script.py"
        assert result["type"] == "text"
        assert "print('Hello, World!')" in result["content"]
        assert result["mime_type"] == "text/plain"

    def test_processes_image_file(self):
        """Test processing an image file."""
        # Use valid PNG magic bytes
        content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        result = process_uploaded_file(content, "photo.png")

        assert result["filename"] == "photo.png"
        assert result["type"] == "image"
        assert result["mime_type"] == "image/png"
        # Content should be base64 encoded
        assert base64.b64decode(result["content"]) == content

    def test_rejects_unsupported_file(self):
        """Test that unsupported files are rejected."""
        content = b"some binary data"
        with pytest.raises(FileProcessingError) as exc_info:
            process_uploaded_file(content, "archive.zip")
        assert "Unsupported file type" in str(exc_info.value)

    def test_rejects_disguised_file(self):
        """Test that files with mismatched content/extension are rejected."""
        # PNG content with JPG extension
        png_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        with pytest.raises(FileProcessingError) as exc_info:
            process_uploaded_file(png_content, "fake.jpg")
        assert "content does not match" in str(exc_info.value)


class TestFormatFileContext:
    """Tests for format_file_context function."""

    def test_formats_text_file_context(self):
        """Test formatting text file context."""
        files = [{
            "filename": "script.py",
            "type": "text",
            "content": "print('hello')",
            "mime_type": "text/plain"
        }]
        result = format_file_context(files)

        assert "<uploaded_file name=\"script.py\">" in result
        assert "print('hello')" in result
        assert "</uploaded_file>" in result

    def test_formats_image_file_context(self):
        """Test formatting image file context."""
        files = [{
            "filename": "photo.png",
            "type": "image",
            "content": "base64data",
            "mime_type": "image/png"
        }]
        result = format_file_context(files)

        assert "<uploaded_image name=\"photo.png\">" in result
        assert "</uploaded_image>" in result

    def test_handles_multiple_files(self):
        """Test formatting multiple files."""
        files = [
            {
                "filename": "file1.txt",
                "type": "text",
                "content": "content1",
                "mime_type": "text/plain"
            },
            {
                "filename": "file2.py",
                "type": "text",
                "content": "content2",
                "mime_type": "text/plain"
            },
        ]
        result = format_file_context(files)

        assert "<uploaded_file name=\"file1.txt\">" in result
        assert "<uploaded_file name=\"file2.py\">" in result

    def test_returns_empty_for_no_files(self):
        """Test that empty string is returned for no files."""
        assert format_file_context([]) == ""
        assert format_file_context(None) == ""

    def test_handles_markdown_with_code_blocks(self):
        """Test that markdown content with triple backticks is handled."""
        files = [{
            "filename": "readme.md",
            "type": "text",
            "content": "# Title\n```python\nprint('hello')\n```",
            "mime_type": "text/plain"
        }]
        result = format_file_context(files)

        # XML tags should contain the content without breaking
        assert "<uploaded_file name=\"readme.md\">" in result
        assert "```python" in result
        assert "</uploaded_file>" in result


class TestGetSupportedExtensions:
    """Tests for get_supported_extensions function."""

    def test_returns_text_extensions(self):
        """Test that text extensions are returned."""
        result = get_supported_extensions()
        assert "text" in result
        assert ".txt" in result["text"]
        assert ".py" in result["text"]
        assert ".log" in result["text"]

    def test_returns_image_extensions(self):
        """Test that image extensions are returned."""
        result = get_supported_extensions()
        assert "image" in result
        assert ".png" in result["image"]
        assert ".jpg" in result["image"]

    def test_returns_size_limits(self):
        """Test that size limits are returned."""
        result = get_supported_extensions()
        assert "max_text_size_mb" in result
        assert "max_image_size_mb" in result
        assert result["max_text_size_mb"] > 0
        assert result["max_image_size_mb"] > 0
