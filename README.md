# Gundam SEED: Rengou vs. Z.A.F.T. Portable — English fan translation (v0.4.2)

An English translation patch for the Japanese PSP game **Kidou Senshi Gundam SEED: Rengou vs. Z.A.F.T. Portable**
(game ID **ULJM05238**), built from your own copy of the game.

This repository contains **only** tools, English text and our own patch code. It contains no game data: no ISO,
no EBOOT, no archive entries, no textures, no Japanese script. Every game-derived file is produced on your machine
from your own legally obtained copy and stays in the git-ignored `work/` folder.

| | |
|---|---|
| Status | v0.4.2 — playable start to finish in **PPSSPP**; not for real PSP hardware (see Known issues) |
| Translated | 300 mission files (names, objectives, briefings), 257 unit descriptions, ~1000 EBOOT strings (menus, memory-stick messages, network text, battle dialogue, tutorial captions, unit/pilot names), ~113 menu/HUD pictures, select-screen label models |
| Engine work | proportional font for the system text renderer, variable-width text for name tags, pilot-select names, message boxes, battle dialogue and tutorial captions |

> **Help wanted: playtesting.** This needs more people playing it. If you find a bug, crash or anything that looks wrong, please [open an issue on GitHub](https://github.com/andrewjose/gundam-seed-rengou-vs-zaft-translation/issues) and include the patch version, your PPSSPP version and device, where it happened (mode and mission), and a screenshot of any untranslated, cut-off or garbled text.

## How to install and play

There is no ready-made patch to download yet: you build the English game yourself from your own copy, with one command. In short:

1. Get your own ISO of the Japanese game (**ULJM05238**, MD5 `0d4dd06ba223f7ff60e05d9f61483905`).
2. Install [Python](https://www.python.org/) 3.10 or newer, then run `pip install -r requirements.txt` and `scripts/fetch_fonts.sh` in this folder.
3. In [PPSSPP](https://www.ppsspp.org/), turn on *Settings → Tools → Developer tools → "Dump decrypted EBOOT.BIN on game boot"* and start the unmodified game once.
4. Run `python3 build/build.py --iso your.iso --eboot-dump PSP/SYSTEM/DUMP/ULJM05238.BIN --workdir work --chd`.
5. Load the ISO or CHD from `work/out/` in PPSSPP (1.17 or newer) on PC, Android or a handheld. It won't run on a real PSP yet.

[What you need](#what-you-need) and [Building](#building) below have the details.

Documentation comes in three levels:

- [docs/overview.md](docs/overview.md) — what the patch does, in plain language
- [docs/engineering.md](docs/engineering.md) — for software engineers new to ROM hacking: how the game stores
  things and how each problem was solved
- [docs/technical.md](docs/technical.md) — for ROM hackers: offsets, routines, formats, commands, dead ends
- [CHANGELOG.md](CHANGELOG.md) — version history
- [translations/glossary.md](translations/glossary.md) — canonical English names

## What you need

- Python 3.10+ and `pip install -r requirements.txt`
- Your own ISO of the game. It must be the retail image of **ULJM05238** with MD5
  `0d4dd06ba223f7ff60e05d9f61483905` (the build refuses other images unless you pass `--skip-md5`).
- [PPSSPP](https://www.ppsspp.org/) (1.17 or newer; tested with 1.20.4) to dump the decrypted EBOOT and to play.
- Fonts: Roboto Condensed is included (`fonts/`, OFL). DejaVu Sans 2.37, Inter 4.0 and Poppins are downloaded by
  `scripts/fetch_fonts.sh` into `fonts/fetched/` (or install them system-wide, e.g. Debian/Ubuntu
  `fonts-dejavu-core fonts-inter`).

## Building

1. **Dump the decrypted EBOOT.** In PPSSPP: *Settings → Tools → Developer tools → "Dump decrypted EBOOT.BIN on game
   boot"*, then start the unmodified game once. PPSSPP writes `ULJM05238.BIN` into its `PSP/SYSTEM/DUMP/` folder.
   The build checks its SHA-1 (`4c3a90ff39a817f9087019eb0dc1450ce00a6f24`).
2. **Fetch fonts:** `scripts/fetch_fonts.sh`
3. **Build:**

   ```sh
   python3 build/build.py --iso /path/to/your/ULJM05238.iso \
                          --eboot-dump /path/to/PSP/SYSTEM/DUMP/ULJM05238.BIN \
                          --workdir work --chd
   ```

   The patched image is written to `work/out/` as an ISO (and a CHD with `--chd`). A full run takes 1–2 minutes.
   Paths can also be set once in `config.local.toml` (copy `config.example.toml`) or with the environment
   variables `GSEED_WORK`, `GSEED_XDATA`, `GSEED_EBOOT`, `GSEED_FONTS`.
4. **Play** the ISO or CHD in PPSSPP.

Run single steps with `--steps`, e.g. `--steps text,xdata,iso` after editing mission text.
Steps: `extract, eboot, text, unpack, glyph, images, atlas, xdata, iso, chd`.

### What is automated and what is not

| Step | Automated | Reproduces the released v0.4.2 build |
|---|---|---|
| EBOOT (strings + all code patches) | yes | **byte-exact** — the result is checked against MD5 `1667c483ad06c3cfbe3455389aba9ce9` |
| Mission text (AFS 174–473), unit text AFS 172 | yes | byte-exact |
| Unit text AFS 173 | yes | byte-exact (v0.4.2 restored the pointer table that the v0.4.1 build had zeroed) |
| Label models (AFS 12, 140), pilot-name glyph sheets (AFS 2, 11, 124, 129, 130, 134, 135, 137, 138) | yes | byte-exact (with the font versions above) |
| ~113 menu/HUD pictures (70 entries incl. the glyph bases) | yes | 55 entries byte-exact; 13 differ in a few anti-aliased pixels because the tested build was made in several incremental passes (≤ 1.8 % of pixels, visually identical) |
| VWF glyph atlases (AFS 10, 1677) | yes | the 96 glyph cells match; unused parts of the textures differ |
| Dumping the decrypted EBOOT | **manual** (PPSSPP) | — |
| Playtesting | **manual** | — |
| Re-signing the EBOOT for real hardware | **not done** | — |

The patched EBOOT is stored decrypted in the ISO. PPSSPP runs it; a real PSP would need it re-signed.

### Editing the translation

- Missions: `translations/missions.json` — AFS index → 10 slots (arc, name, 3 win and 3 lose conditions,
  2 briefing lines). Keep each line inside the measured box width (see docs/technical.md).
- Unit descriptions: `translations/units.json` — keyed by SHA-1 of the original Shift-JIS string.
- EBOOT text: `translations/eboot_strings.json` — keyed by file offset, each with a byte budget. Battle-dialogue and
  tutorial lines are re-laid out by the VWF code patch, so editing them also needs the generators in `tools/vwf/item3`
  (developer route, docs/technical.md).
- Menu pictures: `tools/images/specs/*.json` (box, English text, font and style per region).
- Name tags: `tools/glyph/pilotname/names_fw.py` (8 characters max); select-screen labels: `tools/glyph/labels/names.py`.

## Repository layout

```
build/build.py          one-command pipeline
gseed/                  shared helpers: config/paths, font lookup, hash-verified patching
patches/eboot_v041.json EBOOT code/data patch (runs verified by SHA-1 of the bytes they replace)
patches/stages/         developer stage (v0.3.2 EBOOT) for regenerating the VWF patches
translations/           English text only, keyed by AFS index/slot, file offset or SHA-1
tools/core              AFS reader, mission parser, ISO patching (ISO9660 record relocation)
tools/xdata             pack container + LZ codec, unpack/repack, GIM reader
tools/text              mission/unit text inserter
tools/eboot             string inserter, patch applier, proportional-font patch
tools/images            menu-picture builder (specs → redrawn GIMs)
tools/glyph             PMF2 label models, pilot-name glyph sheets, name-table EBOOT generator
tools/vwf               variable-width-font items (name tags, message box, dialogue, tutorial, pilot select)
tools/chd               pure-Python ISO → CHD v5 writer and verifier
scripts/                fetch_fonts.sh, scrub_check.sh (pre-publish check)
```

## Known issues (v0.4.2)

- Emulator only: the EBOOT is unsigned/decrypted.
- Battle dialogue and tutorial captions were verified in an emulated harness and previews but have not been
  seen in actual play yet.
- Ad Hoc multiplayer untested.
- Unit/pilot name tags are limited to 8 characters, so some names are abbreviated.
- Saves made with the Japanese version show wrong letters in player names entered in kana.
- Copyright lines remain in Japanese.
- ZAFT-side unit descriptions ("New unit received...", upgrade notes; AFS 173) were blank in v0.4.1 because of an
  insertion bug, and are fixed in v0.4.2. The fix is checked byte-for-byte but these messages have not yet been seen
  in play (they appear when a ZAFT unit is unlocked or upgraded in Mission mode).

## Credits

- Translation, reverse engineering and tooling: andrewjose, with Claude (Anthropic) doing the translation,
  analysis and code.
- Fonts: Roboto Condensed (Google, SIL OFL 1.1, `fonts/RobotoCondensed-OFL.txt`), DejaVu Sans (Bitstream Vera
  licence / public domain changes), Inter (Rasmus Andersson, SIL OFL 1.1), Poppins (Indian Type Foundry, SIL OFL 1.1).
  Only Roboto Condensed is redistributed here; the others are downloaded with their licence files.
- CHD format: compatible with MAME `chdman` / libchdr (no code from them is included).
- Licence for the code in this repository: to be decided by the author (none granted yet).

## Disclaimer

This is an unofficial fan project, not affiliated with Bandai Namco, Sunrise or Sony. No game data is included or
distributed. Please buy and support the official release; build the patch only from a copy you own.
