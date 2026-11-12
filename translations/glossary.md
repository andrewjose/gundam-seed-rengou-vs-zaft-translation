# Glossary (English canonical names)

Canonical English spellings used across the patch (missions, unit descriptions, EBOOT text, menu images,
name tags). Romanisations follow the official Bandai / English-subtitle usage. The Japanese side of the
working glossary is intentionally not published; this list is what the translation must stay consistent with.

## Factions, places, ships
ZAFT · Earth Alliance (short: Alliance) · Earth Forces · Orb · PLANTs (singular PLANT) · Clyne Faction ·
Three Ships Alliance · Le Creuset Team · Joule Team · Waltfeld Team · Zala Team · "Legged Ship" (ZAFT nickname
for the Archangel, keep the quotes) · special assault ship

Archangel · Dominion · Eternal · Kusanagi · Vesalius · Gamow · Lesseps · Bosgoroth-class · Nazca-class ·
Laurasia-class · Drake-class · Nelson-class · Agamemnon-class · Izumo-class · Aegis-class ship

Jachin Due · Boaz · Artemis · Heliopolis · Junius Seven · Mendel · Operation Spit Break · Alaska / JOSH-A ·
Panama · Carpentaria · Onogoro Island · Red Sea · Indian Ocean · desert · debris belt · space zone / sector ·
L4 colony · Morgenroete · 8th Fleet · Resistance (Desert Dawn) · GENESIS · FAITH

## Terms
MS · MA · mobile suit · mobile armor · G-weapon · G Project · Biological CPU · Extended · Neutron Jammer ·
DRAGOON · nuclear · Phase Shift armor · Mirage Colloid · Striker Pack · Aile · Sword · Launcher · METEOR ·
captured · stolen · mass-production · prototype · pre-production · general-purpose · heavy assault machine gun

Mission conditions: "Time limit reached" · "Your unit destroyed" · destroy · drive off / repel · sink ·
shoot down · escape / withdraw

## Mobile suits and armors
Strike · Aile / Launcher / Sword Strike · Duel · Duel AS · Buster · Blitz · Aegis · Freedom · Justice ·
Providence · Calamity · Forbidden · Raider · Strike Rouge ("S.Rouge" if tight) · Astray · M1 Astray ·
Strike Dagger · Long Dagger · Duel Dagger · 105 Dagger · Buster Dagger · Moebius · Moebius Zero · Skygrasper ·
Mistral · Guul

GINN · GINN High Maneuver · GINN Ocher · GINN Wasp · CGUE · DINN · BuCUE · LaGOWE · GOOhN · ZnO · GuAIZ ·
GuAIZ R · ZAUT

Force / Sword / Blast Impulse · Chaos · Abyss · Gaia · Saviour · ZAKU Warrior · ZAKU Phantom · GOUF · Windam ·
Dagger L · Freedom / Justice with METEOR

## People
Kira · Athrun · Lacus · Cagalli · Mu / La Flaga · Murrue · Natarle · Yzak · Dearka · Nicol · Rau Le Creuset ·
Le Creuset · Waltfeld · Aisha · Patrick Zala · Siegel Clyne · Azrael · Orga · Clotho · Shani · Halberton ·
Sahib · Uzumi · Miguel · Heine

Name tags are limited to 8 characters; the abbreviations used there are listed in
`tools/glyph/pilotname/names_fw.py`.

## Style rules
- ASCII only in text the game renders through its Shift-JIS path: no full-width characters, curly quotes,
  em/en dashes or ellipsis characters (use "...").
- Japanese corner brackets become double quotes; lenticular brackets around mission arcs become `[X]`.
- Tone: concise military briefing. ZAFT / Alliance briefings are terse imperatives ("Destroy the enemy.");
  Orb / Clyne-side briefings are polite requests ("Please protect ..."). Keep that difference.
- Each source line is its own on-screen line. Never add line breaks; stay inside the measured width.
