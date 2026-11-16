# Technical reference (v0.4.6)

For ROM hackers who want to study or reproduce the work. Target: ULJM05238 (retail ISO MD5
`0d4dd06ba223f7ff60e05d9f61483905`). Engineer-level explanations are in [engineering.md](engineering.md).

Conventions: *VA* = virtual address in the PSP's user memory, *file* = offset in the decrypted EBOOT.
`file = VA - 0x08804000 + 0x54` (single PT_LOAD segment, file offset 0x54 → 0x08804000; static ELF, no relocation).

---------------------------------------------------------------------------------------------------------------------

## 1. Disc layout

| Path | Notes |
|---|---|
| `PSP_GAME/SYSDIR/EBOOT.BIN` | encrypted PRX-style EBOOT; decrypted dump 3,278,112 bytes, SHA-1 `4c3a90ff39a817f9087019eb0dc1450ce00a6f24` |
| `PSP_GAME/USRDIR/X_DATA.BIN` | CRI AFS, 1,737 entries, 103,155,712 bytes |
| `PSP_GAME/USRDIR/Y_DATA.BIN` | ADX audio (untouched) |
| `PSP_GAME/USRDIR/DUMMY.BIN` | ~268 MB padding; used as relocation space for a grown X_DATA |

## 2. X_DATA.BIN

**AFS:** `"AFS\0"`, u32 N, N × (u32 offset, u32 size), then (u32 name-table offset, u32 size) = (0, 0) in this
game. Entries are 0x800-aligned. `tools/core/afs.py`, `tools/xdata/repack.py rebuild_afs` (keeps header area,
order and alignment; offsets shift when sizes change).

**Pack container** (1,341 of the entries; `tools/xdata/pack.py`):
```
sector 0: u32 N, N × u32 entry, zero padding to 0x800
  entry = (flags << 30) | sector_count ; flags bit 0 (0x40000000) = LZ-compressed ; entry 0 = empty slot
data from 0x800, each sub-file sector_count * 0x800 bytes, in entry order; total = (1 + Σ sectors) * 0x800
```
`rebuild_pack` reuses the original on-disk bytes of unchanged sub-files (rebuilding all packs unchanged is
byte-identical, `repack.py selftest`).

**LZ** (decoder at VA 0x088D24E4, called with src+4; `tools/xdata/lz.py`):
```
u32 decompressed size (used only by the loader for buffer sizing)
repeat: u16 control word, then 16 items, bits consumed MSB first
  bit 0: literal u16 (2 bytes)
  bit 1: token v = u16; L = v >> 11 (words), D = v & 0x7FF (words)
         L == 0 -> an extra u16 follows with L
         D == 0, L > 0 -> L words of zero
         D == 0, L == 0 (0000 0000) -> end of stream
         else copy L words from out - 2D (overlapping, byte-wise equivalent)
```
The encoder is greedy hash-chain matching on 16-bit words; `compress_opt` (more tries) is used when a rebuilt entry
must fit its old slot.

## 3. Text in X_DATA

**Missions — AFS 174–473** (`tools/core/mission.py`, `tools/text/insert_text.py`): header of 5 u32; `header[3]` = file
offset of a table of 10 absolute string offsets (terminated by 0 / a value ≥ the table offset). Slots:
`arc, name, win1, win2, win3, lose1, lose2, lose3, brief1, brief2`; empty slots point at an empty string. Strings
are cp932, NUL-terminated, packed; the string area ends at the table. The inserter packs the English back to back
from `ptrs[0]`, zero-fills to the table and rewrites the 10 pointers. Alignment of strings was tested and is not
needed. Data: `translations/missions.json` (`entries[afs][slot]`).

*Width model (v0.4.4).* Briefing, condition and title lines are drawn by the proportional sceFont renderer (§4.3),
so an ASCII line is `Σ (bitmapWidth + bitmapLeft + 1)` in size/20 units (space 11, double-byte 20). The metrics were
taken from PPSSPP's `assets/flash0/font/jpn0.pgf` (FTT-NewRodin Pro DB; parsed as in PPSSPP `Core/Font/PGF.cpp`,
glyph header bits w7 h7 left7 top7 after a 14-bit size field). The box limits measured in v0.2 with a FreeSans
model convert to briefing 576, condition 292, title 373 units. v0.4.4 checked all 300 files: 11 fields over the
limit were refit; "Destroy 20/30 target drones" stay 1 unit (0.3 %) over. Lose conditions are outcomes
("Strike destroyed"), win conditions orders ("Destroy Strike"): the v0.2 inserter mapped one English string per
Japanese string, so the same "gekiha" (destroy) phrase got the win wording in lose slots.

**Unit descriptions — AFS 172 / 173:** u32 pointer table (first pointer / 4 = entry count; 304 and 320 entries,
some 0), strings in 0x40-byte slots. **Every original offset must be kept** — relocating strings (v0.1) crashes
Arcade mode (found by bisecting AFS entries in PPSSPP). English is written over each slot, NUL-padded to the next
string start, truncated if longer. Data: `translations/units.json`, keyed by `sha1(cp932 bytes of the original)`.

*v0.4.1 build note:* the original inserter treated pointer value 0 as a string at offset 0; in AFS 173 the first
table word starts with byte 0x00, so that "empty string" zero-filled the whole table (0..0x500). The tested v0.4.1
image contains that zeroed table. `insert_text.py` skips empty strings and keeps the table; AFS 172 was unaffected
(its first table bytes decode as a control character and were skipped). Fixed in v0.4.2: the 0x500-byte table of
AFS 173 (entry at X_DATA offset 0x00B0A000 in the shipped image) was written back from the original, string bodies
unchanged; X_DATA size and layout are identical to v0.4.1. Not yet seen in play.

## 4. EBOOT

### 4.1 Strings (`translations/eboot_strings.json`, `tools/eboot/insert_strings.py`)
1,005 strings in `.rodata/.data` (regions: battle_dialogue 692, unit_pilot_names 167, system_memstick 90, misc 30,
network 18, system_menu 5, misc_menu 4), written in place: English + zero fill to `budget` bytes (the slot length
without its terminator). Each entry carries `orig_sha1` of its budget bytes; one string (id 958, the copyright
line) is untranslated. The original pointer words still reference the same addresses.

### 4.2 Code/data patch (`patches/eboot_v041.json`, `tools/eboot/apply_patch.py`)
2,578 runs (maximal runs of changed bytes relative to the strings-inserted EBOOT), each
`{file_off, orig_sha1, new_hex, stage}`; the file also pins `input_sha1`, `after_strings_sha1`, `output_sha1`.
Final EBOOT MD5 `1667c483ad06c3cfbe3455389aba9ce9`. Runs by stage: v0.2 proportional font 37, v0.3 atlas/string
re-layout 1,740, v0.3 pilot/unit names 378, v0.4 VWF 403, v0.4.1 20.

Developer route (regenerates the same EBOOT from the generators):
```sh
python3 tools/eboot/insert_strings.py EBOOT_dec.BIN work/stage/s1.elf
python3 tools/eboot/apply_patch.py work/stage/s1.elf work/stage/eboot_v03d.elf patches/stages/eboot_v03d.json
python3 tools/vwf/apply_all.py            # items 1,2,3,3b,A,B,A2 -> work/stage/eboot_v041.elf (same MD5)
# regenerate item patches: tools/vwf/item*/build.py (item A2 needs work/stage/eboot_v041a.elf = apply_all --items 1,2,3,3b,A,B)
```
All item generators reproduce the committed patch JSONs byte-for-byte from these stages.

### 4.2a v0.4.4+ EBOOT changes (`translations/eboot_strings_v044.json`, `tools/eboot/insert_v044.py`)
Applied to the v0.4.1 EBOOT (MD5 `1667c483…`) → v0.4.6 EBOOT MD5 `d8de64db99dae4ad07e8cae7bbf56bd2`
(`de002b7995f74c00c501d94108b51236` with `--no-itemC`). 30 strings, 1 blob, 2 pointers, then item C (§4.7):
| file | what |
|---|---|
| 0x21BBE8 | memory-stick fragment (message box, `%n` = KB count, drawn as full-width digits by the game) |
| 0x21D52C–0x21D5C4 | save-data DETAIL text, built by 0x088DE4F4 with strcpy/strcat/sprintf into 0x08DB6C40 and copied by 0x088F4E04 into the PspUtilitySavedataSFOParam (title 0x80, savedataTitle 0x80, detail 0x400) through the SJIS→UTF-8 converter 0x0884415C; shown by the PSP save dialog |
| 0x24C228 | SFO title of the save data (save dialog) |
| 0x2A9084 | lobby "1P is setting up. Please wait." (blinking, 0x089A19C0) |
| 0x2BEBB8 | network "Press any button." (0x089C302C, pointer variable 0x08AC2B80) |
| 0x21B58C–0x21B5D4 | ad hoc team list [TEAM A]/[TEAM B]/CPU/1P–4P (were full-width Latin; drawn left-aligned by 0x088CDB6C through 0x088D24DC) |
| 0x1DB488–0x1DB4BB + pointers 0x1DB4F8/0x1DB4FC | `sprintf("%s%s", word[x != 2], fragment)` at 0x088715A8: the two word slots hold "Return to the menu" / "Return to the lobby", the fragment is "?" (was "Menu" + ": Return to this screen?") |
| 0x21B848, 0x21BAAC | "Load this data?", "Overwrite data?" (v0.4.5) |
| 0x29F3EC… (7) | tutorial lines (pool of the v0.3 re-layout) |
| 0x2A03F4, 0x2A16A4, 0x2A347C | "!?" → "?!" |
Message-box acknowledgements (`%r`) draw the ▼ arrow (0x088D1884), not a "Yes" label, so no one-button "Yes" exists.

### 4.3 Proportional system font (v0.2) — `tools/eboot/propfont.py`
Renderer 0x088D2330 (wrapper 0x088D24DC) draws Shift-JIS through sceFont glyphs cached in 20 px cells and advanced
every glyph by `size` except U+0020 (size/2). 59 words at 0x088D23CC–0x088D24B7 (file 0xCE420–0xCE50B) are
replaced: non-ASCII keeps the full-cell advance; ASCII (UCS-2 < 0x80) advances by
`(bitmapLeft + bitmapWidth + 1) * size / 20` from `sceFontGetCharInfo` (spacing constant at 0x088D2484). Tail of
the new code:
```mips
sltiu $v1,$s0,0x80        ; ASCII?
lui   $v0,0x3f80
beqz  $v1,full_cell
mtc1  $v0,$f2
lw    $v0,0x90($sp)       ; bitmap left
lw    $v1,0x94($sp)       ; bitmap width
addu  $v0,$v0,$v1
addiu $v0,$v0,1           ; + spacing
mtc1  $v0,$f2
cvt.s.w $f2,$f2
lui   $v0,0x41a0          ; 20.0
mtc1  $v0,$f3
div.s $f2,$f2,$f3
lwc1  $f0,0x40($sp)
mul.s $f2,$f2,$f22        ; * size
add.s $f0,$f0,$f2         ; pen x += advance
```
A `--mode half` variant (3 words, ASCII = size/2) exists for comparison. The 0xCE420–0xCE50B range is off-limits to
every later patch (`apply_all.py` asserts it).

### 4.4 Pilot / unit names (v0.3) — `tools/glyph/pilotname`
- Converter 0x089BE1B4 maps a 2-byte SJIS character to (cell, page) through tables 0x08AB1294 / 0x08AB1368 /
  0x08AB13C4. Glyph page at file 0x2AD2E8, keyboard table at file 0x2A6B90 (59 entries, ends with a kana sentinel,
  checked by hash), ranking defaults at file 0x2A6398 (30 × 0x20, 16-byte SJIS fields; matched by SHA-1).
- Glyph sheets: kana cells replaced with Latin letters + digits (layout `ABCDEFGHIJ KLMNOPQRST UVWXYZabcd efghij*k*l
  mnopqrstuv wxyz.-'!?`, 10 per row; digits in row 6) in 9 copies: AFS 2/2 img0 (G1 14 px), 134/1 img5 (G1),
  124/1 img0 + 129/1 img1 (G2 14 px), 11/1 img1 + 130/1 img0 (G3 18 px, keyboard), 135/1 img3, 137/1, 138/1
  (G4 18 px). Glyphs from Inter (Bold/Medium/SemiBold/ExtraBold) at 8× supersampling with optional outline.
- Names: full-width English (`names_fw.py`, ≤ 8 characters, ship names ≤ 9) placed in the CRI ADX error-message
  text at file 0x1D2104–0x1D281D; six pointer tables repointed (VA 0x08A1D368 suits, 0x08A1DD04 pilots,
  0x08A1DA80 ships, 0x08A1DB34 enemies, 0x08A1DDF0 commanders, 0x08A1DED8 soldiers).
- **Never touch file 0x1D25B8 (`"AFS\0"`).** It sits inside that message area but is the magic the ADX/AFS loader
  compares; overwriting it gave a black screen at boot (first v0.3 attempt, found by bisection).
- `build_eboot.py` generated the runs against the v0.3 EBOOT (not reproducible from this repo; its output is part of
  `patches/eboot_v041.json`); `apply_eboot_patch.py` applies the stored list with hash checks.

### 4.5 Battle dialogue and tutorial (v0.3 pair glyphs → v0.4 VWF)
Battle dialogue: 0x08988B88 builds up to 4 line pointers → 0x08988C84 per line (steps text by 2 bytes; lookup
0x08988CD4 in 4 glyph lists at `*(0x08AAA1C4 + 4*set)`) → drawer 0x08988EDC (cell = index + base[set] from
0x08AAA1D4, 16 cells/row, 16×16 texels, quad 12.5×13 px, 0xFF ends the line). Line buffer 0x1E bytes. Atlas:
AFS 1677 sub 0 (GIM 256×512, 8bpp swizzled), registered at 0x0888D014 into 0x08ECE99C[0].

Tutorial: 0x089C1788 sets up 2 lines from 0x08AB2190; converter 0x089C1850; lookup 0x089C18E4 (one list at
`*(0x08AB1A0C)`, index % 13 == 12 = narrow cell, unmatched → 0x4D skipped); drawer 0x089C1A88 (13 cells/row,
14×14 texels, advance 14 or 7, line centred by width units). Line buffer 0x32 bytes. Atlas: AFS 10 sub 1 image 0.

*v0.3 "pair glyphs"* (superseded, generator not included): English stored as ASCII, each aligned letter pair is one
lookup unit; lists rebuilt from the pairs actually used (dialogue 503 cells = capacity, tutorial 195 of 216), atlas
cells redrawn with two 7-texel letters; strings and lists repacked into a free-space pool and 828 pointers updated.
That re-layout is why dialogue strings are not at their original offsets in v0.4.1.

*v0.4 VWF* (`tools/vwf/item3/build.py`, `build_tut.py`, atlases `tools/vwf/atlas_vwf.py`):
- 0x08988C84 rewritten: writes `0xFE` + the 4-byte source-string pointer into the line buffer.
- Width table (96 bytes, ASCII 0x20–0x7F) at 0x08988CAC inside the now-dead lookup.
- 0x08988EDC rewritten in place (ends before 0x089890E4): draws the ASCII string glyph by glyph, cell = ch − 0x20
  (16/row, glyph at texel +1,+1), advance `(w + 1) * 12.5 / 14`, max 187.5 px; returns the same "line finished" flag.
- Tutorial: 0x089C1850 stores `0xFE` + pointer, returns the char count and writes the width in 7-unit steps to `*a2`
  (consumed unchanged by the centring code at 0x089C1980); width table at 0x089C18E4; drawer 0x089C1A88 uses the
  14×14 cell model (+0x960), pen += (w + 1) × scale.
- Strings rewritten in place with the pair-alignment spaces removed (374 dialogue, 18 tutorial lines). Widest
  dialogue line 176.8 px (limit 187.5), tutorial 310 px (limit 350).
- Glyphs: DejaVu Sans Condensed Bold 12 px at 8× supersampling, quantised to the atlas palette's alpha ramp.

### 4.6 Name tags, message box, pilot select (v0.4 / v0.4.1) — `tools/vwf`
Code caves: CRI ADXT "parameter error" debug strings at file 0x1D2C10–0x1D33A8 (VA 0x089D6BBC…), plus dead code
replaced by the items. `apply_all.py` checks hashes, overlaps, the prop-font block and the `AFS\0` magic.

| Item | Runs | What |
|---|---|---|
| 1 name tags | 8 | width tables G1 0x089D6BBC, G2 0x089D6C24, T18 0x089D6C8C; core `VW_CORE` 0x089D6CF4, `VW_SJ` 0x089D6D90, per-site stubs `VW_A..G`; cave file 0x1D2C10–0x1D2EFC |
| 2 message box | 14 | renderer 0x088D15E8: `VW_MB` 0x089D7030, `VW_STRW` 0x089D7054, `VW_LW` 0x089D70C0, `VW_ADVCH` 0x089D6FAC; sites 0x088D1658, 0x088D1748, 0x088D17FC, 0x088D180C, 0x088D1D24; ASCII "Yes"/"No" at 0x08A1F6EC/0x08A1F6F4 (the ASCII path used to pass a constant space → blank labels) |
| 3 / 3b | 377 / 21 | dialogue / tutorial VWF (4.5) |
| A | 2 | stub 0x089D6EB0, site 0x0899C060 in 0x0899BF6C (pilot name, record+6, x = index × 17.5). Kept; the screen using this path was not identified (unverified) |
| B | 4 | Yes/No centring: %y handler calls 0x088FFC78(0, x, y) with boxes centred at x+21 / x+91; labels drawn at centre − w/2; sites 0x088D1A38, 0x088D1ADC; `VW_LW`+0x64 counts %y as 14 so the caller's +98 still gives the original 112 px block. Tested in PPSSPP |
| A2 | 2 | SELECT A PILOT big name: draw callback 0x0899D314 (codes at obj+0x170 filled by 0x0899D1F8, 8 slots, x = slot × 17.75 on the 18 px sheet); stub `VW_PN` 0x089D6ED0 sums proportional widths of the previous slots into f20; site 0x0899D36C. Tested: Kira, Sai, Cagalli, Asagi, Mayura, Juri |

| C (v0.4.4) | 10 | `VW_BLEN` 0x089D723C (+1 entry 0x089D7244, +2 entry 0x089D724C), file 0x1D3290–0x1D3368 in the ADXT strings after item B; replaces `jal strlen` (0x0880D70C) at 9 sites, see §4.7 |

Assembly: `tools/vwf/masm.py` (llvm-mc, mipsel, mips32r2, no relocations). Emulated tests: `tools/vwf/emu.py`
(Unicorn) — `test_item1.py`, `test_sites.py`, `item2/test.py`, `item3/test.py`, `item3/test_tut.py`,
`itemA/test.py`, `itemA2/test.py` (they render previews into `<work>/preview/`).

### 4.7 Item C — byte-count width estimates (v0.4.4) — `tools/vwf/itemC`
Nine call sites compute a text width as `strlen × 7` px (2 bytes = one 14 px full-width cell) to centre or fit text.
`VW_BLEN(s)` returns `(units + 5) / 10` with units as in §3 (ASCII via the glyph cache 0x08979F40 exactly like item 2's
`VW_ADVCH`; space 11; lead byte ≥ 0x80 = 20 and skip 2), i.e. the byte count of a Japanese string of the same
width: Japanese input returns its strlen. Frame 0x50, saves ra/s0/s1, the +k entries store k at sp+0x48. Every site
was checked for caller-saved registers live across the call (none).
| site | caller | drawn |
|---|---|---|
| 0x0888AE54 | 0x0888ACBC | "1P is in control. Please wait." x = (480 − n·7)/2 |
| 0x088715B0 | 0x0887126C | "%s%s" lobby confirm |
| 0x088717F4 (+1) | 0x0887126C | "1P is selecting from the menu…" (n − 1) |
| 0x089A19E8 | 0x089A19C0 | "1P is setting up…" |
| 0x089C2F5C (+2) | 0x089C2F3C | network messages, (n − 2) (the Japanese ended with a 2-byte full stop) |
| 0x089C305C | 0x089C302C | "Press any button.", x = (448 − n·7)/2 + 32 |
| 0x089AEEF0 | 0x089AEE7C | mission info titles: size 13 (14 for one line) until (n/2)·size ≥ 197, then size = 196/(n/2), centred on the estimate |
| 0x089AF72C, 0x089AF800 | 0x089AF690 | mission info win / lose lines: size 13 until n/2 ≥ 15, then 182/(n/2) |
The panel's data is resource 3 (`0x088DC5E4(3)`), the loaded mission file's pointer table (titles +0, win +8,
lose +0x14). Tested in PPSSPP (mission info and pause > Mission info). Emulated test: `tools/vwf/itemC/test.py`.

## 5. Graphics in X_DATA

**GIM** (`tools/images/gimcodec.py`): index8 (fmt 5) swizzled images (16-byte × 8-row tiles), 256-entry palettes
(RGBA8888 or 5551). `encode()` writes indices/palette back into a copy of the original bytes, preserving header,
chunk layout and pitch/height padding.

**Image specs** (`tools/images/specs/*.json`, 72 files, 113 pictures, 438 regions): file = `<afs>_<sub>`,
per picture `erase` default, `defaults` (font face key, size, colour, outline, shadow) and `regions`:
`box` (x0,y0,x1,y1 texels), optional `erase_box`, `erase` (transparent / fill / `inpaint_bright` with `erase_thr`),
`en`, `align`, `valign`, `ss` (supersampling, 4 for Roboto Condensed), `min_squeeze`, `tracking`, `custom`
(`custom_ops.py`: `strip` for the 3-slice stage-name banners in 128_1 / 132_1 at x194–255, y 0/20/40;
`eaf` builds "E. A. F." in 133_1 pic 6 from the pixels of the neighbouring "Z. A. F. T." label; `label_rgba`
inpaints RGB and alpha over sprite edges). Fixed-rect sprite pieces: pause 2_13, options 2_20, button config 2_11
(each word must stay inside its piece; rectangles inferred from glyph gaps and confirmed in game). Font faces:
`rc`/`rc6` Roboto Condensed 700/600, `cond` DejaVu Sans Condensed Bold, `sans` DejaVu Sans Bold, `semi` Inter
SemiBold. Rendering → per-picture palette quantisation (premultiplied nearest colour, changed pixels only).

**Label models** (`tools/glyph/labels`): AFS 12 (arcade/free-battle suit select: `sel12_lXX` big names with optional
subtitle, `sel12_qXX` weapon strips) and AFS 140 (mission-mode list `misres_mirXX`). Sub 0 = PMF2 (objects at
`u32 table @0x20`; per object a 0x100 header, GE command list: 0x01 vaddr, 0x12 vtype 0x102 (u16 UV, s16 XYZ),
0x04 prim, 0x0B end), sub 1 = 512×512 index8 texture. Left half of the 12 texture is cleared and re-packed on
shelves; names drawn with Poppins Bold outlined (4×) / Inter Bold; quads' x1 and u1 rewritten
(raw x per texel 77.07 for AFS 12, (16457+16163)/222 for AFS 140), bounding spheres recomputed.

**Polish rounds v0.4.4–v0.4.6** (`tools/images/polish`, build step `polish`): made on top of the v0.4.2 pictures, so the
step first builds `X_DATA_base.BIN` (original + `afs_new`) and unpacks it to `<work>/polish/out`; `ORIG` is the
original unpack (`<work>/xd_out`). Rounds run in order; each round's entry is rebuilt with `rebuild_pack` from the
newest earlier version of that entry (afs_out_r5 > r4 > r3 > afs_out > base), changing only its own sub-files:
| round | script | entries (sub) |
|---|---|---|
| 1 | `fixes.py` | 2_0 help-bar legends (rects from the EBOOT sprite table, 8-byte records x,y,w,h,0,0,0,tex at file 0x1DE925–0x1DE9C5), 133_1 pic8, 1608_1, 562–578 map labels, 105–121 banners (rebuilt from the original texture, underline rows masked out of the inpaint), 2_20 Options grid, 1684 credits, copyright 2_16 pic0 + 9_9 pic5 |
| 2 | `fixes2.py` | PMF2 quad re-layouts: 129 sub 0/1 lobby (l1a–l26), 124 sub 0/1 VS prompts (k60–k64), 11 sub 0/1 link status (k70/k71, k7b–k7d); help words 11_1 pic1, 130_1 pic0, 133_1 pic6/8; credits artist names |
| 3 | `fixes3.py`, `fixes3.py banner` | 2 sub 10/11 Pause > Buttons (keyconf00_kc08–kc11), 2_15 phase banner, 125_1 headers, 1609_1 "OK" |
| 4 | `fixes4.py` | 133 sub 0 `selmi02_si22` header gap, 131_1 pic1 "EAF" |
| 5 | `fixes5.py` | 125 sub 0/1 VS. SETTINGS labels rc18 (selvs02_k69–k71, BGM k9f) |
| 6 | `fixes6.py` | 1609 sub 0/1 result buttons (result02_rm03/rm17/rm18), 2 sub 19/20 Options labels (menu01_g08–g50) |
PMF2 layout objects (§5 Label models format): texture index = u32 at object+0x74 (0 = sub-1 pic0 …), UV u16 =
texel·32768/texture width, vtype 0x102, prim 4 = 4-vertex strip per quad. A message is one object whose quads cut
word pieces out of the texture; the Japanese word order is just the quads' x positions. Rounds 2–6 draw whole English
phrases into free texture space and rewrite the object's quads in place (same prim count and byte length; unused
quads get four identical vertices = zero area). `check_pmf()` asserts that only the edited objects' vertex arrays
change. `pmfdump.py <afs>` / `pmfuse.py <afs> [tex]` list objects and quads.

**Atlases**: see 4.5. `atlas_vwf.py` writes cells 0–95 only; the rest of each texture is unused by the VWF code.

## 6. ISO and CHD

- `tools/core/isoreloc.py` parses `/PSP_GAME/USRDIR` directory records and rewrites extent/size (both-endian).
- `tools/core/build_iso.py src dst xdata eboot` (dst = full copy of src): if X_DATA fits the space before Y_DATA it
  is written in place, otherwise into DUMMY.BIN's extent (DUMMY's record is shrunk); EBOOT.BIN is overwritten in
  place (same size, unencrypted). PPSSPP loads unencrypted EBOOTs; real hardware needs a signed one (§6.1).
- `tools/chd/iso2chd.py` writes CHD v5 like `chdman createdvd -hs 2048 -c zlib` (zlib / uncompressed / self-reference
  hunks, Huffman-coded compressed map, `DVD ` metadata, raw and overall SHA-1). `chdverify.py --against ISO`
  decompresses every hunk, checks CRCs and SHA-1s and compares byte-for-byte. Verified against chdman 0.264 and
  libchdr; the v0.4.1 CHD was verified byte-identical on the tester's machine.
- `tools/chd/chdsplice.py old.chd new.iso out.chd --range START:LEN ...` makes the CHD for a small ISO change in
  about 40 s instead of a full encode: hunks covering the ranges (and SELF-hunks that referenced them) are
  recompressed, all other compressed data is copied in contiguous blocks, offsets shift, and the map, raw SHA-1 and
  overall SHA-1 are rebuilt. v0.4.2 was made this way (one hunk, 160868) and checked byte-identical with
  `chdverify.py --against`.

### 6.1 Hardware: signed EBOOT, PARAM.SFO, EBOOT.PBP (v0.4.3) — `tools/psp/psp_hw.py`

- PARAM.SFO is at sector 22144 (472 bytes). TITLE is fmt 0x0204, max_len 128; the original is 56 bytes. The English
  title is also 56 bytes and is written in place (index entry `len` updated, slot zero-padded). 45 bytes change.
- EBOOT.BIN: extent 32, 3,278,112 bytes (1,601 sectors, slot 3,278,848). `sign_np -elf in out 0` (sign_np v1.0.2,
  swarzesherz/sign_np @ ac77d56) gives a ~PSP container of 3,278,448 bytes: modname `seedpsp`, elf_size 3,278,112,
  tag 0xD91609F0 (retail is 0xC0CB167C, game-specific). Output is deterministic. Written into the same extent and
  zero-padded; the directory record in /PSP_GAME/SYSDIR (sector 24, record 0xC098) gets the new size, both-endian.
- PBP: `sign_np -pbp -c ISO EBOOT.PBP JP0000-ULJM05238_00-0000000000000000 0` (fixed key, compressed NPUMDIMG).
  The input must already carry a signed EBOOT. sign_np copies PARAM.SFO (CATEGORY becomes `EG`), ICON0, PIC0, PIC1
  and SND0 from the ISO. Release v0.4.3: 532,666,000 bytes, DATA.PSAR at 0x9B900. sign_np crashed on a minimal
  test ISO holding only UMD_DATA/PARAM.SFO/EBOOT, so use the full image.
- CHD after these changes: `chdsplice.py ... --range 49152:2048 --range 65536:3278848 --range 45350912:472`
  (hunks 24, 32–1632, 22144); verified byte-identical with `chdverify.py --against`.
- Checked in PPSSPP 1.20.4: ISO and PBP both boot, main menu, Mission > Load message box (VWF item 2). Not checked
  on hardware. Decrypting the signed EBOOT back with pspdecrypt was not possible in the build environment; the
  header fields above and the PPSSPP boot are the evidence.

## 7. Reproducibility

Measured for v0.4.6 from the retail X_DATA and the PPSSPP EBOOT dump (`--steps eboot,text,unpack,glyph,images,atlas,polish,xdata`,
fonts DejaVu 2.37 / Inter 4.0 / Poppins from `scripts/fetch_fonts.sh`). The xdata step prints the comparison against
`patches/release_v046_xdata.json` (sha1 of every entry of the tested image).
| Output | Result vs. the tested v0.4.6 image (X_DATA MD5 `38b26dce…`) |
|---|---|
| EBOOT | identical, MD5 `d8de64db99dae4ad07e8cae7bbf56bd2` checked (and the v0.4.1 stage `1667c483…` on the way) |
| AFS 172, 173, 174–473 | identical |
| 1723 of 1737 entries | identical |
| AFS 2, 124, 125, 129, 130, 133, 1609 (polished) | same size; 0.01–1.3 % of the pixels of one picture each differ by more than 24/255 — inherited from their v0.4.2-level base below. Run on a byte-identical v0.4.2 base the polish scripts reproduce all 46 polished entries byte-for-byte |
| AFS 10, 132, 138, 1323–1325 | v0.4.2-level differences (the release was built incrementally; the repo does one pass) |
| AFS 1677 | glyph cells identical, unused texture area and size differ (49,152 vs 32,768 bytes) |
So the repo build is not MD5-identical to the release X_DATA (it is 103,079,936 bytes); reproducing those 14 entries
exactly would need the tested pixels, which are game-derived and not stored here. Font versions matter: upstream
DejaVu 2.37 TTFs differ slightly from Debian's build.

Font versions matter for exactness: upstream DejaVu 2.37 TTFs differ slightly from Debian's build.

## 8. Tools and commands

```sh
python3 tools/xdata/unpack.py [X_DATA.BIN] [out_dir]      # every entry/sub-file + index.tsv
python3 tools/xdata/repack.py selftest                   # pack rebuild identity + LZ round trip
python3 tools/core/sjscan.py FILE...                     # find Shift-JIS runs
python3 tools/xdata/scan_sjis.py                         # inventory of Japanese text in unpacked files (local output)
python3 tools/xdata/mdis.py 0x088D2330 40                # disassemble (capstone)
python3 tools/eboot/propfont_gen.py                      # re-assemble the prop-font block (keystone)
python3 tools/glyph/labels/verify.py                     # label sheets before/after (local previews)
python3 tools/vwf/refs.py | dead.py | freespan.py | live.py   # xref / dead-code / free-span / register-liveness helpers
python3 tools/eboot/insert_v044.py work/stage/eboot_v041.elf out.elf [--no-itemC]   # v0.4.4+ strings + item C
python3 tools/vwf/itemC/build.py [eboot_v041.elf]            # regenerate itemC/patch.json + layout.json
python3 tools/vwf/itemC/test.py [eboot_v041.elf]             # emulated VW_BLEN check (Unicorn)
python3 tools/images/polish/run.py                           # polish rounds 1-6 -> work/afs_polish (build step 'polish')
python3 tools/images/polish/pmfdump.py 129                   # PMF2 objects of <work>/polish/out/129_0.bin
python3 tools/images/polish/pmfuse.py 2 0                    # every quad of a PMF2 with its texel rect (texture 0)
```

## 9. Dead ends

- Building `pspdecrypt` locally to decrypt the EBOOT: not possible in the build environment; PPSSPP's dump is used.
- Aligning mission strings like the original: unnecessary, packed strings work.
- Writing overflowing strings past the end of their file ("spillover"): worked, abandoned for in-place fits.
- Feeding ASCII directly to the atlas renderers: garbled output (they look up 2-byte units) → pair glyphs (v0.3),
  then VWF (v0.4).
- Relocating unit-description strings: Arcade crash (v0.1).
- Using the ADX error-text area without excluding `AFS\0`: black screen (v0.3 first attempt).
- Fixing the lobby / VS prompt word order in the EBOOT (v0.4.4): the messages are not assembled by code from piece
  IDs but are PMF2 layout objects; the fix is a quad edit in the data (§5).
- Fixing the off-centre network messages by padding strings with trailing spaces: works only within byte budgets and
  would also change the strings' other users; replaced by item C.
- Making the mission-info panel fit by padding titles to `units/10` bytes: not enough slack in many mission files;
  replaced by item C.
- Locating a layout table for the Arcade phase banner pieces (2_15): none found (no PMF2 quad match), so the pieces
  were reworded inside their own rects.

## 10. Known issues

v0.4.4–v0.4.6 images use the unsigned decrypted EBOOT (emulator only) until the §6.1 signing step is rerun and
tested; battle dialogue (690 lines, triggered at battle start by 0x0898700C from the battle-scene init 0x088C3BCC)
and tutorial captions not yet seen in actual play; Ad Hoc untested (the lobby and link screens changed in v0.4.4–
v0.4.6 were checked statically); name tags ≤ 8 characters (the Morassim tag reads "Morasim"); kana names from Japanese
saves show wrong letters (kana cells now hold Latin glyphs); EBOOT string 958 (copyright) untranslated, the title-screen
copyright picture is English since v0.4.4; item A's screen unverified; signed EBOOT/PBP untested on hardware;
the X_DATA is not MD5-reproducible from this repo (§7).
