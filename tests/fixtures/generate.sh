#!/usr/bin/env bash
# Generate synthetic test fixtures for eyeroll.
# Run from repo root: bash tests/fixtures/generate.sh
#
# These fixtures exercise format handling, frame extraction,
# audio detection, duration edge cases, and image input paths.
# They are NOT meant to test analysis quality — use real recordings for that.

set -uo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)/synthetic"
rm -rf "$DIR"
mkdir -p "$DIR"

FAILED=0

gen() {
    # Run ffmpeg, track failures but don't abort
    if ffmpeg "$@" 2>/dev/null; then
        return 0
    else
        echo "  FAILED: ${*: -1}" >&2
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "Generating synthetic test fixtures in $DIR ..."

# ===========================================================================
# VIDEO FIXTURES — different formats
# ===========================================================================
echo ""
echo "--- Video formats ---"

gen -y -f lavfi -i "color=c=0x1a1a2e:s=1280x720:d=10:r=30" \
    -c:v libx264 -pix_fmt yuv420p "$DIR/standard_10s.mp4" && echo "  standard_10s.mp4"

gen -y -f lavfi -i "color=c=0x2e1a2e:s=1280x720:d=10:r=30" \
    -c:v libvpx-vp9 -b:v 1M "$DIR/standard_10s.webm" && echo "  standard_10s.webm"

gen -y -f lavfi -i "color=c=0x1a2e1a:s=1280x720:d=10:r=30" \
    -c:v libx264 -pix_fmt yuv420p "$DIR/standard_10s.mov" && echo "  standard_10s.mov"

gen -y -f lavfi -i "color=c=0x2e2e1a:s=1280x720:d=10:r=30" \
    -c:v libx264 -pix_fmt yuv420p "$DIR/standard_10s.avi" && echo "  standard_10s.avi"

gen -y -f lavfi -i "color=c=0x1a2e2e:s=1280x720:d=10:r=30" \
    -c:v libx264 -pix_fmt yuv420p "$DIR/standard_10s.mkv" && echo "  standard_10s.mkv"

# ===========================================================================
# DURATION EDGE CASES
# ===========================================================================
echo ""
echo "--- Duration edge cases ---"

gen -y -f lavfi -i "color=c=0x4a1a2e:s=1280x720:d=2:r=30" \
    -c:v libx264 -pix_fmt yuv420p "$DIR/short_2s.mp4" && echo "  short_2s.mp4"

gen -y -f lavfi -i "color=c=0x1a4a2e:s=1280x720:d=5:r=30" \
    -c:v libx264 -pix_fmt yuv420p "$DIR/short_5s.mp4" && echo "  short_5s.mp4"

gen -y -f lavfi -i "color=c=0x1a1a2e:s=1280x720:d=150:r=30" \
    -vf "hue=H=2*PI*t/30" -c:v libx264 -pix_fmt yuv420p \
    "$DIR/long_150s.mp4" && echo "  long_150s.mp4"

# ===========================================================================
# AUDIO VARIANTS
# ===========================================================================
echo ""
echo "--- Audio variants ---"

gen -y -f lavfi -i "color=c=0x1a1a4e:s=1280x720:d=10:r=30" \
    -f lavfi -i "sine=frequency=440:duration=10" \
    -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest \
    "$DIR/with_audio.mp4" && echo "  with_audio.mp4"

gen -y -f lavfi -i "color=c=0x4e1a1a:s=1280x720:d=10:r=30" \
    -c:v libx264 -pix_fmt yuv420p -an \
    "$DIR/silent.mp4" && echo "  silent.mp4"

gen -y -f lavfi -i "color=c=0x2e1a4e:s=1280x720:d=10:r=30" \
    -f lavfi -i "sine=frequency=300:duration=10" \
    -f lavfi -i "sine=frequency=600:duration=10" \
    -filter_complex "[1:a][2:a]amix=inputs=2:duration=shortest[aout]" \
    -map 0:v -map "[aout]" \
    -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest \
    "$DIR/with_complex_audio.mp4" && echo "  with_complex_audio.mp4"

# ===========================================================================
# MULTI-SCENE VIDEO (color changes — tests frame dedup)
# ===========================================================================
echo ""
echo "--- Multi-scene ---"

gen -y -f lavfi -i "color=c=0xff4444:s=1280x720:d=20:r=30" \
    -vf "hue=H=2*PI*floor(t/4)/5" -c:v libx264 -pix_fmt yuv420p \
    "$DIR/multi_scene.mp4" && echo "  multi_scene.mp4"

# ===========================================================================
# IMAGE FIXTURES
# ===========================================================================
echo ""
echo "--- Image formats ---"

gen -y -f lavfi -i "color=c=0x1a1a2e:s=1280x720:d=1:r=1" \
    -frames:v 1 -update 1 "$DIR/screenshot.png" && echo "  screenshot.png"

gen -y -f lavfi -i "color=c=0x2e1a1a:s=1280x720:d=1:r=1" \
    -frames:v 1 -update 1 "$DIR/screenshot.jpg" && echo "  screenshot.jpg"

gen -y -f lavfi -i "color=c=0x2e2e1a:s=1280x720:d=1:r=1" \
    -frames:v 1 -update 1 "$DIR/screenshot.bmp" && echo "  screenshot.bmp"

gen -y -f lavfi -i "color=c=0x1a2e2e:s=1280x720:d=1:r=1" \
    -frames:v 1 -update 1 "$DIR/screenshot.gif" && echo "  screenshot.gif"

gen -y -f lavfi -i "color=c=0x2e1a2e:s=1280x720:d=1:r=1" \
    -frames:v 1 -update 1 "$DIR/screenshot.tiff" && echo "  screenshot.tiff"

# WebP — needs libwebp encoder, skip if unavailable
if ffmpeg -encoders 2>/dev/null | grep -q libwebp; then
    gen -y -f lavfi -i "color=c=0x1a2e1a:s=1280x720:d=1:r=1" \
        -frames:v 1 -c:v libwebp -update 1 "$DIR/screenshot.webp" && echo "  screenshot.webp"
else
    # Fall back: convert from PNG using sips (macOS)
    if command -v sips >/dev/null 2>&1 && [ -f "$DIR/screenshot.png" ]; then
        cp "$DIR/screenshot.png" "$DIR/screenshot_tmp.png"
        sips -s format webp "$DIR/screenshot_tmp.png" --out "$DIR/screenshot.webp" >/dev/null 2>&1 \
            && echo "  screenshot.webp (via sips)" \
            || echo "  SKIP: screenshot.webp (no webp encoder)"
        rm -f "$DIR/screenshot_tmp.png"
    else
        echo "  SKIP: screenshot.webp (no webp encoder)"
    fi
fi

echo ""
echo "--- Image edge cases ---"

gen -y -f lavfi -i "color=c=0x1a1a2e:s=3840x2160:d=1:r=1" \
    -frames:v 1 -update 1 "$DIR/screenshot_4k.png" && echo "  screenshot_4k.png"

gen -y -f lavfi -i "color=c=0x4a4a4a:s=320x240:d=1:r=1" \
    -frames:v 1 -update 1 "$DIR/thumbnail.png" && echo "  thumbnail.png"

gen -y -f lavfi -i "color=c=0x0d1117:s=1280x720:d=1:r=1" \
    -frames:v 1 -update 1 "$DIR/dark_mode.png" && echo "  dark_mode.png"

gen -y -f lavfi -i "color=c=0xf5f5f5:s=1280x720:d=1:r=1" \
    -frames:v 1 -update 1 "$DIR/light_mode.png" && echo "  light_mode.png"

# ===========================================================================
# EDGE CASES
# ===========================================================================
echo ""
echo "--- Edge cases ---"

head -c 512 "$DIR/standard_10s.mp4" > "$DIR/corrupt_truncated.mp4"
echo "  corrupt_truncated.mp4"

touch "$DIR/empty.mp4"
echo "  empty.mp4"

cp "$DIR/standard_10s.mp4" "$DIR/unsupported.xyz"
echo "  unsupported.xyz"

# ===========================================================================
# Summary
# ===========================================================================
echo ""
echo "--- Summary ---"
COUNT=$(find "$DIR" -type f | wc -l | tr -d ' ')
echo "Generated $COUNT fixture files ($FAILED failed)"
echo ""
du -sh "$DIR"
echo ""
echo "Regenerate with: bash tests/fixtures/generate.sh"

exit $FAILED
