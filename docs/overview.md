# What this patch does (plain-language overview)

*Gundam SEED: Rengou vs. Z.A.F.T. Portable* is a 2-on-2 Gundam action game for the PSP that was only released
in Japan. This patch turns its text into English so you can play it without reading Japanese.

## What you will notice

- **Missions** — every mission name, objective ("Destroy the enemy flagship", "Your unit destroyed") and briefing
  is in English.
- **Menus** — the main menu, options, button setup, pause menu, character and mobile-suit select screens, results
  screens and on-screen labels are in English. Many of these were pictures, not text, so they were redrawn.
- **Names** — mobile suits and pilots have English names everywhere, including the small name tags in battle.
  Name tags hold at most 8 letters, so some names are shortened (for example "Forbid." for Forbidden).
- **Messages** — memory-stick, network and confirmation messages are in English; "Yes" and "No" sit in the middle
  of their buttons.
- **Battle chatter and tutorial captions** — translated, with letters that take only as much room as they need.
- **Readable text** — the game was built for Japanese characters, which are all the same width. English text looked
  stretched and spaced out, so the patch teaches the game to place each letter by its real width.

## What it does not do (yet)

- It has only been tested in the PPSSPP emulator. Since 0.4.3 it should also run on a PSP with custom firmware and
  on a PS Vita with Adrenaline, but nobody has tried that yet. A PSP without custom firmware cannot run it.
- Battle chatter and tutorial captions have been checked in a test setup but not yet seen while playing.
- Local wireless (Ad Hoc) play has not been tested.
- The copyright notice stays in Japanese.
- If you continue a save from the Japanese version, names typed in Japanese letters will look wrong.

## How you get it

The repository does not contain the game. You need your own copy of the game, and the build script makes the
English version from it on your computer (see the README). The result is a disc image you open in PPSSPP. For a modded PSP or Vita there is also a version that goes in the
memory stick's game folder and shows up with an English name in the menu.

## Version history in short

- **0.1** missions and unit texts (crashed in Arcade mode)
- **0.2** crash fixed, readable letter spacing, menus and messages
- **0.3** menu pictures, battle chatter, tutorial, pilot names
- **0.3.1 / 0.3.2** button setup, map labels, more menu pieces, stage names, music names
- **0.4** nicer fonts, better-spaced name tags, messages, battle chatter and tutorial
- **0.4.1** better-spaced names on the pilot-select screen, centred Yes/No
- **0.4.2** fixed blank unit descriptions on the Z.A.F.T. side (shown when you unlock or upgrade a suit)
- **0.4.3** English game title in the menu; versions for modded PSPs and the Vita (memory-stick game folder)
