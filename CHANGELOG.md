# Changelog

All versions were tested in PPSSPP (1.20.4) on the user's PC unless noted.

## v0.4.1
- **Pilot-select big name now proportional** (VWF item A2): the SELECT A PILOT panel draws the name through the
  object draw callback at 0x0899D314; its fixed 17.75 px per-slot advance is replaced by the proportional pen of the
  18 px name-tag sheet. Tested: Kira, Sai, Cagalli, Asagi, Mayura, Juri.
- **Yes/No labels centred** in their highlight boxes (VWF item B, on top of the message-box item). Tested.
- VWF item A (pilot-select name through 0x0899BF6C) is kept; it patches a related draw path whose screen has not
  been identified, so it is unverified.
- Public repository import: tools, English-only translation data, hash-verified EBOOT patch, three-level docs.
  The repo build keeps the original pointer table of AFS 173 (see Known issues in the README).

## v0.4
- Typography polish of the menu pictures: tight UI labels moved to Roboto Condensed (rendered at 4x and
  downsampled for natural spacing), one font/size per menu.
- Name tags (pilot/unit names) proportional (VWF item 1).
- Message box: proportional ASCII and fixed Yes/No labels, which were blank before because the ASCII path passed a
  constant space (VWF item 2).
- Battle dialogue and tutorial captions switched from the "pair glyph" atlases to single-glyph variable-width
  text (VWF item 3 / 3b).

## v0.3.2
- Composite labels built from several sprite pieces, Yes/No pieces, stage-name banners wrapped across three slices,
  BGM names, "E. A. F." badge built from the pixels of the neighbouring "Z. A. F. T." label.

## v0.3.1
- Button-configuration screen and map labels.

## v0.3
- ~110 menu/HUD pictures redrawn in English with an exact-layout GIM encoder.
- Select-screen labels (PMF2 quad models, AFS 12 and 140) rebuilt with English text.
- Battle dialogue and tutorial captions through "pair glyph" atlases (two letters per glyph cell, no code changes).
- Pilot/unit names: kana glyph cells replaced by Latin letters in 9 sheet copies, full-width English names in a code
  cave. The first attempt overwrote the `AFS\0` string used by the ADX loader and the game booted to a black
  screen; found by bisecting, fixed before release.

## v0.2
- Fixed the Arcade-mode crash of v0.1: unit descriptions (AFS 172/173) must keep their original string offsets.
- Proportional font for the system text renderer (59-word patch at 0x088D23CC).
- ~1000 EBOOT strings translated in place (menus, memory stick, network, dialogue, names).
- 101 mission lines refitted after measuring the real box widths in PPSSPP.

## v0.1
- Missions (AFS 174–473) and unit descriptions (AFS 172/173) translated. Arcade mode crashed.
