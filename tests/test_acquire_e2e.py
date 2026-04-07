"""E2E tests for the acquire module using real synthetic fixtures."""

import os

import pytest

from eyeroll.acquire import acquire, detect_media_type, _resolve_local


# ---------------------------------------------------------------------------
# detect_media_type with real files
# ---------------------------------------------------------------------------

class TestDetectMediaTypeReal:
    def test_mp4(self, mp4_video):
        assert detect_media_type(mp4_video) == "video"

    def test_webm(self, webm_video):
        assert detect_media_type(webm_video) == "video"

    def test_mov(self, mov_video):
        assert detect_media_type(mov_video) == "video"

    def test_avi(self, avi_video):
        assert detect_media_type(avi_video) == "video"

    def test_mkv(self, mkv_video):
        assert detect_media_type(mkv_video) == "video"

    def test_png(self, png_image):
        assert detect_media_type(png_image) == "image"

    def test_jpg(self, jpg_image):
        assert detect_media_type(jpg_image) == "image"

    def test_bmp(self, bmp_image):
        assert detect_media_type(bmp_image) == "image"

    def test_gif(self, gif_image):
        assert detect_media_type(gif_image) == "image"

    def test_tiff(self, tiff_image):
        assert detect_media_type(tiff_image) == "image"

    def test_unsupported(self, unsupported_file):
        with pytest.raises(ValueError, match="Unsupported file type"):
            detect_media_type(unsupported_file)


# ---------------------------------------------------------------------------
# _resolve_local with real files
# ---------------------------------------------------------------------------

class TestResolveLocalReal:
    def test_video_formats(self, mp4_video, webm_video, mov_video, avi_video, mkv_video):
        for path in [mp4_video, webm_video, mov_video, avi_video, mkv_video]:
            result = _resolve_local(path)
            assert result["media_type"] == "video"
            assert result["file_path"] == path
            assert result["source_url"] is None
            assert len(result["title"]) > 0

    def test_image_formats(self, png_image, jpg_image, bmp_image, gif_image, tiff_image):
        for path in [png_image, jpg_image, bmp_image, gif_image, tiff_image]:
            result = _resolve_local(path)
            assert result["media_type"] == "image"
            assert result["file_path"] == path

    def test_4k_image(self, image_4k):
        result = _resolve_local(image_4k)
        assert result["media_type"] == "image"

    def test_thumbnail(self, thumbnail_image):
        result = _resolve_local(thumbnail_image)
        assert result["media_type"] == "image"


# ---------------------------------------------------------------------------
# acquire() with real local files
# ---------------------------------------------------------------------------

class TestAcquireLocalReal:
    def test_acquire_mp4(self, mp4_video):
        result = acquire(mp4_video)
        assert result["media_type"] == "video"
        assert os.path.isfile(result["file_path"])

    def test_acquire_webm(self, webm_video):
        result = acquire(webm_video)
        assert result["media_type"] == "video"

    def test_acquire_mov(self, mov_video):
        result = acquire(mov_video)
        assert result["media_type"] == "video"

    def test_acquire_png(self, png_image):
        result = acquire(png_image)
        assert result["media_type"] == "image"

    def test_acquire_jpg(self, jpg_image):
        result = acquire(jpg_image)
        assert result["media_type"] == "image"

    def test_acquire_unsupported_extension(self, unsupported_file):
        with pytest.raises(ValueError, match="Unsupported file type"):
            acquire(unsupported_file)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestAcquireEdgeCases:
    def test_empty_file_detected_as_video(self, empty_video):
        """An empty .mp4 is still detected as video by extension."""
        result = acquire(empty_video)
        assert result["media_type"] == "video"
        assert os.path.getsize(result["file_path"]) == 0

    def test_corrupt_file_detected_as_video(self, corrupt_video):
        """A truncated .mp4 is still detected as video by extension."""
        result = acquire(corrupt_video)
        assert result["media_type"] == "video"

    def test_file_sizes_are_reasonable(self, mp4_video, png_image):
        """Synthetic fixtures should be non-trivial in size."""
        assert os.path.getsize(mp4_video) > 1000
        assert os.path.getsize(png_image) > 100
