#!/usr/bin/env bash
# Download the fonts the image/glyph builders render with into fonts/fetched/ (git-ignored).
# Roboto Condensed is already in fonts/ (OFL). Licences are saved next to each font.
# Versions used for v0.4.1: DejaVu 2.37, Inter 4.0, Poppins (google/fonts main).
# Alternatively install them system-wide (Debian/Ubuntu: fonts-dejavu-core fonts-inter) - the resolver
# (gseed/fonts.py) also searches the usual system font directories.
set -euo pipefail
D="$(cd "$(dirname "$0")/.." && pwd)/fonts/fetched"
mkdir -p "$D"; cd "$D"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
echo "DejaVu 2.37"
curl -fsSL -o "$tmp/dejavu.tar.bz2" https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.tar.bz2
tar xjf "$tmp/dejavu.tar.bz2" -C "$tmp"
cp "$tmp"/dejavu-fonts-ttf-2.37/ttf/DejaVuSans{,-Bold,Condensed-Bold}.ttf .
cp "$tmp"/dejavu-fonts-ttf-2.37/LICENSE DejaVu-LICENSE.txt
echo "Inter 4.0"
curl -fsSL -o "$tmp/inter.zip" https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip
python3 - "$tmp/inter.zip" <<'PY'
import sys, zipfile, os
z = zipfile.ZipFile(sys.argv[1])
want = {'Inter-Bold.otf', 'Inter-SemiBold.otf', 'Inter-Medium.otf', 'Inter-ExtraBold.otf', 'LICENSE.txt'}
for n in z.namelist():
    b = os.path.basename(n)
    if b in want and ('/otf/' in n or b == 'LICENSE.txt'):
        open('Inter-LICENSE.txt' if b == 'LICENSE.txt' else b, 'wb').write(z.read(n)); want.discard(b)
if want - {'LICENSE.txt'}: raise SystemExit('missing from Inter zip: %s' % want)
PY
echo "Poppins"
curl -fsSL -o Poppins-Bold.ttf   https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf
curl -fsSL -o Poppins-Medium.ttf https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Medium.ttf
curl -fsSL -o Poppins-OFL.txt    https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/OFL.txt
ls -la "$D"
