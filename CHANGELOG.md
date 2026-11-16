# Changelog

All versions were tested in PPSSPP (1.20.4) on the user's PC unless noted.

## v0.4.6
- **Options and VS. SETTINGS labels** (AFS 2 sub 19/20, AFS 125 sub 0/1): every row label is now one Roboto Condensed
  Bold 18 piece at the same on-screen size in both menus (was a mix of word pieces, sizes and the original "BGM"
  art). Rows that the game assembled from Japanese word pieces (Boost + Gauge + Amount, Awaken + Gauge + Rate,
  Awaken + Time) are single quads now; wording matches VS. SETTINGS: Boost Gauge, Awaken Gauge Rate, Awaken Time.
- **Auto Save** in Options > Load/Save ("Automatic" did not fit its slot), Damage Level / Awaken Time slots re-split,
  BGM "Auto Select" gap closed.
- **Link-battle result buttons** (AFS 1609): "Lobby Menu" was drawn across two pieces and showed as "Lobby M"; now
  "Lobby" and "Menu" are separate pieces, and the "VS Select" / "Lobby" / "End Link" texts are centred on their buttons.
- Tested in PPSSPP: ISO MD5 `2b35a01807a17774bdc305d65b79a61c` (SHA-1 `eef908518062c14c442bd8ff96b91e91e4a984aa`,
  CRC32 `69aba421`), X_DATA MD5 `38b26dce2d4d5bab2fceef4f08bfb664` (103,063,552 bytes), EBOOT MD5
  `d8de64db99dae4ad07e8cae7bbf56bd2`. EBOOT unchanged since v0.4.5.
- **Known issue: emulator only.** v0.4.4-v0.4.6 images carry the unsigned decrypted EBOOT; the v0.4.3 signing /
  EBOOT.PBP step (`tools/psp/psp_hw.py`, sign_np) has not been rerun on them.

## v0.4.5
- Memory-stick prompts: "Load it?" -> "Load this data?", "Overwrite?" -> "Overwrite data?".
- **Arcade phase banner** (AFS 2 sub 15): the pieces read "ENEMY UNITS  DESTROY THEM!"; now target pieces end with a
  colon and the orders were reworded: ENEMIES: / SHIPS: / ENEMY TARGETS: / ENEMY MOBILE SUITS: + DESTROY ALL! /
  WIPE THEM OUT!
- **Pause > Buttons** (PMF2 AFS 2 sub 10 + texture sub 11): all four labels one size and baseline, "(Awaken)" moved
  to a free texture slot, label quads aligned in one column.
- VS. SETTINGS header words in the settings' face (AFS 125), standalone "OK" on the link result screen redrawn to
  match (AFS 1609), level-select header "Choose the game level" gap closed (PMF2 AFS 133 sub 0), mission-menu level
  panel "EA" -> "EAF" (AFS 131).
- Tested in PPSSPP (built on the v0.4.4 kit).

## v0.4.4
- **Mission text polish** (AFS 174-473, 143 files / 202 strings): no more semicolons used as commas or comma splices,
  natural briefings, two wrong unit names (Calamity / Forbidden tests said "X370 Raider"), a broken line join in
  AFS 249 / 444 / 467. 27 lose conditions read as orders ("Destroy Strike") and now read as outcomes ("Strike
  destroyed", "5 Aegis ships sunk"); mission name "Dominion sunk" -> "Sink the Dominion". Every field re-measured
  with the PSP system font's real advances (see docs/technical.md §3); 11 fields refit.
- **Unit descriptions** (AFS 172/173): 62 distinct lines (193 slots) without semicolons or "perf."/"proto"
  abbreviations. Offsets and pointer tables unchanged.
- **EBOOT** (`translations/eboot_strings_v044.json`): the last Japanese reachable text in the executable is English:
  the save-dialog title and "Mission Mode Status" detail, the memory-stick "%nKB more free space" line, the lobby
  "1P is setting up. Please wait." and the network "Press any button."; ad hoc team list labels ([TEAM A], CPU,
  1P-4P) are ASCII instead of full-width; "Menu: Return to this screen?" (Japanese word order) -> "Return to the
  menu?" / "Return to the lobby?"; tutorial punctuation; "!?" -> "?!".
- **Item C (new code):** nine routines estimated text width as bytes x 7 px (every character 2 bytes, 14 px). With
  English that pushed lobby/network messages off centre and let the mission info panel overflow its boxes or squash
  titles. They now call `VW_BLEN` (VA 0x089D723C), which measures the real proportional width. Tested in PPSSPP:
  mission info and pause > Mission info.
- **Pictures and layouts** (tools/images/polish, rounds 1-2): help-bar legends redrawn from their exact sprite rects,
  Options grid in one face, mission map labels one size, location-banner smudges removed, level-select help row,
  "inbound!" popup, credits quote marks and artist names, **English copyright line** on the title screen
  ("SOTSU AGENCY / SUNRISE / MBS"), and the ad hoc lobby / VS prompts / link status messages rebuilt as whole English
  sentences by re-pointing the PMF2 layout quads (AFS 11, 124, 129, 130).
- Tested in PPSSPP: title, help bar, Mission > Load, mission list, mission info, pause > Mission info.

## v0.4.3
- **Runs on real hardware (CFW/HEN PSP, Vita Adrenaline) — untested on hardware.** The patched EBOOT is now
  fake-signed with `sign_np -elf` (tag 0xD91609F0) and written into its original extent (3,278,112 → 3,278,448 bytes,
  same 1,601 sectors; only the EBOOT.BIN directory record's size changes). `sign_np -elf` is deterministic, so the
  result is reproducible.
- **PSN-style `EBOOT.PBP`** built from the ISO with `sign_np -pbp -c` (NPUMDIMG, fixed key, content ID
  `JP0000-ULJM05238_00-0000000000000000`), for `ms0:/PSP/GAME/ULJM05238/` or a Vita bubble.
- **English XMB title** in PARAM.SFO: "Mobile Suit Gundam SEED: Alliance vs. Z.A.F.T. Portable" (56/128 bytes,
  in place).
- New `tools/psp/psp_hw.py` (title, signing, PBP) and `tools/psp/sfo_set_title.py`. sign_np itself is not included.
- Tested in PPSSPP 1.20.4: both the ISO and the PBP boot to the English main menu and render the proportional
  message box (Mission > Load). Text and game data are unchanged from v0.4.2.

## v0.4.2
- **ZAFT-side unit descriptions restored** (AFS 173). The v0.4.1 inserter read a pointer value of 0 as an empty
  string at offset 0 and zero-filled the whole pointer table (0x000-0x4FF), so every ZAFT "New unit received" and
  upgrade message pointed at an empty string. v0.4.2 writes the original table back; the English strings are
  unchanged. Same-size, in-place change; EBOOT unchanged. Static check only: the messages were not reached in play.

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
