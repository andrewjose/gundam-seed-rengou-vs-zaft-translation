# How the translation works (for software engineers)

This document assumes you can program but have never modified a game. Each section explains a console- or
game-specific idea in terms of ordinary software and then says what we did with it. Exact addresses and formats are
in [technical.md](technical.md); the player-facing summary is in [overview.md](overview.md).

## 1. The starting point: one executable, one big archive

A PSP game disc (UMD) is an ordinary ISO 9660 filesystem image, like a CD-ROM. This game keeps almost everything in
two places:

- `PSP_GAME/SYSDIR/EBOOT.BIN` — the program, a 3 MB MIPS executable. On the disc it is **encrypted and signed** (think
  of a code-signed binary the OS refuses to run if modified). PPSSPP can write out the **decrypted** version while the
  game boots; that dump is a plain static ELF, which is what we patch.
- `PSP_GAME/USRDIR/X_DATA.BIN` — a 100 MB **archive** in CRI's AFS format: a header with a table of (offset, size)
  pairs followed by 1,737 entries, each padded to 2 KB sectors. Think of it as an uncompressed tar file with an index
  but no file names: everything is addressed by **index number**.

Many AFS entries are themselves small containers ("packs") whose sub-files are compressed with the game's own LZ
variant. The tools in `tools/xdata` unpack all of it into numbered files (`<entry>_<subfile>.bin`) and can put changed
sub-files back, recompressing them and recomputing sector counts, while copying unchanged data byte-for-byte.

**How we found the formats:** by looking at the bytes (headers, repeating sector counts) and, for the compression,
by reading the decompression routine in the executable and porting it to Python. The port is checked by rebuilding
every one of the 1,341 packs unchanged and comparing byte-for-byte.

## 2. Text: Shift-JIS strings and pointer tables

Japanese games of this era store text in **Shift-JIS**, a variable-width encoding where ASCII is one byte and
Japanese characters are two bytes. English fits in the ASCII range, so an English string is usually *shorter in
bytes* than the Japanese one it replaces — but not always shorter on screen.

Strings are found through **pointer tables**: arrays of offsets, exactly like an array of `char*` into a string pool.
If you change a string's length you either keep it inside its old slot or move it and update every pointer to it.

- **Missions (300 files):** each file has a small header, a table of 10 pointers (mission arc, name, three win and
  three lose conditions, two briefing lines) and a packed string pool. We rewrite the pool with the English strings
  back to back and rewrite the 10 pointers. Translations are keyed by *(archive index, slot)*, so the repository never
  needs the Japanese text.
- **Unit descriptions (2 files):** also a pointer table, but here moving strings made Arcade mode crash. We found
  that by **bisecting**: building patches with half of the changes reverted until the crash disappeared, then
  narrowing down. The game evidently relies on the original offsets, so every English string is written over its
  original slot (truncated if needed). These translations are keyed by a SHA-1 hash of the original Japanese bytes:
  the inserter hashes each original string at build time and looks the hash up. Hashes let us match without
  publishing the source text.
- **Executable strings (~1,000):** menu text, memory-stick messages, network errors, names and battle dialogue live
  inside the EBOOT. Each was rewritten **in place** within its original byte budget, so no code pointers had to move.

Line lengths: the boxes these strings appear in have fixed pixel widths. We measured the real widths in the emulator
and rewrote 101 mission lines that overflowed.

## 3. Fixed-width vs. variable-width text (VWF)

Japanese text renderers usually advance every character by the same amount ("monospace"), because kana and kanji are
square. Latin letters are not: an `i` is a quarter of the width of a `W`. Printed through a fixed-width renderer,
English looks like `H e l l o`. Fixing that is called adding a **variable-width font (VWF)**: for each character, look
up its real width and advance the pen by that instead.

The game has several independent text systems, and each needed its own fix:

| System | Original behaviour | Fix |
|---|---|---|
| System text (menus, messages) via the PSP font library | every glyph advanced a full cell except the space | 59 instructions rewritten so ASCII advances by the glyph's real metrics from the font library |
| Name tags (pilot/unit names) | full-width letters from a glyph sheet, fixed advance | width tables + new advance code in a code cave |
| Message box | its ASCII path passed a constant space character, so English Yes/No labels were blank | rewritten to measure and draw ASCII; labels centred |
| Battle dialogue, tutorial captions | text drawn from a texture atlas, two bytes per lookup | single-glyph atlas + width table + rewritten line converter and drawer |
| Pilot-select big name | fixed 17.75 px per slot | proportional pen per slot |

Patching machine code: we write small MIPS routines, assemble them at a fixed address (`llvm-mc`), and either
overwrite a function in place or put the new code into a **code cave** — a region of the executable that is never
executed or read in practice. Our caves are debug error-message strings of the CRI audio middleware and lookup
functions made dead by our own rewrites. The routines were tested with **Unicorn** (a CPU emulator library) by
calling the patched functions directly with fake inputs, like unit-testing a function in isolation, before testing
in PPSSPP.

A trap we hit: one "unused" string region contained the literal text `AFS\0`, which the audio loader compares
against when opening archives. Overwriting it gave a black screen at boot. Bisection found it; the build tools now
refuse to touch those 4 bytes.

## 4. Text that is a picture: textures, palettes, sprite pieces

Much of the menu text is not text at all but **images** (GIM, the PSP's texture format). They are 8-bit **indexed**
images — each pixel is an index into a 256-colour palette, like a GIF — stored **swizzled** (in 16×8-byte tiles,
the order the GPU reads fastest).

For each picture, a JSON spec (`tools/images/specs`) lists the regions to replace: a box in texels, how to erase the
Japanese (make transparent, fill, or inpaint from surrounding pixels), the English text, font, size and colour. The
builder renders the English from real fonts at build time (4× supersampled, then downsampled, which gives natural
letter spacing at tiny sizes), quantises the result into the picture's *existing* palette and writes the pixels back
into the original file layout without changing headers. So the repository holds only coordinates, words and style
settings — never pixels from the game.

**Sprite pieces:** many labels are drawn at runtime by cutting fixed rectangles out of a texture and placing them
side by side (for example "Back to" + "Title" from separate pieces). The English for each piece must fit *its own*
rectangle exactly, or letters get clipped. We inferred the rectangles from gaps between Japanese glyphs and checked
them on screen. Stage names are drawn as three 62-pixel slices placed next to each other, so the English name is
rendered as one line and cut into three slices.

**Texture atlases:** battle dialogue and tutorial captions are drawn from a texture full of glyph cells (a sprite
sheet of characters). Version 0.3 used a trick that needed no code changes: since the game looks up two bytes at a
time, every *pair* of English letters ("He", "ll", "o ") became one atlas cell. It worked but was cramped and ran out
of cells. Version 0.4 replaced it with one letter per cell plus a width table and a rewritten drawer (a real VWF).

**3D label models:** the big suit names on the select screens are flat 3D quads (PMF2 models) with texture
coordinates pointing into a label texture. We re-packed the label texture with English names and adjusted the quads'
width and UV coordinates to match.

**Pilot and unit names** use a converter that maps each 2-byte Shift-JIS character to a cell in a glyph sheet. We
replaced the kana cells with Latin letters in all 9 copies of the sheet and pointed the name tables at full-width
English names (one Latin letter per 2-byte cell).

## 5. Putting it back on the disc

The rebuilt archive can be larger than the original because recompressed files change size. The ISO filesystem
stores each file's start sector and length in a **directory record** (like an inode). If the new `X_DATA.BIN` does not
fit its old place, the builder writes it into the space of a large padding file (`DUMMY.BIN`) and edits the directory
records to point there — no other file moves. The decrypted EBOOT replaces the encrypted one in place; PPSSPP accepts
an unencrypted EBOOT, a real PSP would not.

Optionally the ISO is converted to **CHD**, a compressed disc-image format (per-2 KB-block zlib, deduplication of
repeated blocks) that PPSSPP reads directly. The repo's writer is pure Python and its verifier decompresses every
block and compares with the ISO.

## 6. Keeping the repository free of game data

- Translation files contain English only, keyed by archive index + slot, file offset, or SHA-1 of the original bytes.
- The EBOOT patch is a list of byte runs `{offset, sha1 of the bytes being replaced, new bytes}`. The new bytes are
  our code, tables and English text; the hash makes the patcher refuse a wrong input without storing the original.
- Pictures are regenerated from fonts against the user's own files; nothing rendered is committed.
- `scripts/scrub_check.sh` fails the build of a commit if Japanese characters, private paths, raw original bytes,
  large files or game-file extensions appear.

## 7. Trade-offs

- **In-place over relocation.** Rewriting strings in place keeps every pointer valid and avoids crashes like the
  Arcade one, at the cost of tight byte budgets (hence abbreviations, and the 8-character name tags).
- **Emulator-only.** Re-signing the EBOOT for hardware needs tools we did not build; PPSSPP is the target.
- **Reproducible vs. identical.** The EBOOT build reproduces the tested executable bit for bit. The pictures are
  regenerated, so a different font version or a single-pass build can change a few anti-aliased pixels; the
  tested release itself was produced in several incremental passes.
