# Full-width (SJIS) English names for the 14/18px name-glyph system. Max 8 chars each.
SUIT = ["A.Strike","L.Strike","S.Strike","Strike","Strike","S.Rouge","Aegis","Blitz","Buster","Duel","Duel AS",
 "Raider","Calamity","Forbid.","S.Dagger","M1Astray","Freedom","Justice","Provid.","GuAIZ","GuAIZ-C","DINN","DINN-C",
 "CGUE","ZAUT","ZnO","GOOhN","LaGOWE","BuCUE","BuCUE","GINN","GINN","GINN","GINN","R.GINN","G.Ocher","G.Wasp",
 "P.GINN","F.METEOR","J.METEOR","M.Zero","Moebius","Skygrasp","Skygrasp","Skygrasp","Skygrasp","Archangl",
 "Dominion","Kusanagi","Eternal","Vesalius","Gamow","Menelaos","Bernard","Aegis-cl","Lesseps","F.Impuls",
 "S.Impuls","B.Impuls","Saviour","Chaos","Gaia","Abyss","ZAKU W","B.ZAKU P","G.ZAKU W","G.ZAKU W","S.ZAKU P"]
PILOT = ["Kira","Kira","Kira","Mu","Tolle","Sai","Cagalli","Cagalli","Orga","Clotho","Shani","Mayura","Asagi",
 "Juri","Natarle","Murrue","Athrun","Nicol","Yzak","Yzak","Dearka","Rau","Miguel","Waltfeld","Waltfeld",
 "Morasim","Ades","Lacus","Kisaka","EA #0","Orb #0","ZAFT #0","Redcoat","Shinn","Athrun","Sting","Stella",
 "Auel","Rey","Luna","Yzak","Dearka","Kira"]
SHIP = ["Archangel","Izumo","Nazca","Laurasia","Agamemnon","Drake"]   # drawn via 0x089BE144 (max 9)
ENEMY = ["M1Astray","S.Dagger","CGUE","GINN","GINN","GINN","GINN","R.GINN","P.GINN","G.Ocher","G.Wasp","BuCUE",
 "BuCUE","ZAUT","GOOhN","ZnO","DINN","DINN-C","GuAIZ","GuAIZ-C","Moebius","Moebius","Mistral","Guul","H.Track",
 "Nuke Msl","Shuttle","Shuttle","Pod","CGUE","GINN","GINN","GINN","GINN","GINN","GINN","GINN","GuAIZ","GuAIZ",
 "Kira","Athrun","Nicol","Dearka","Yzak","Kira","Athrun","Nicol","Dearka","Yzak","Clotho","Orga","Shani","VTOL"]
CMDR = ["Murrue","Natarle","Milly","Lacus","Waltfeld","Kisaka","Rau","Ades","Dacosta","Azrael","Athha","Natarle","Neo","Meyrin"]
SOLDIER = ["EA-A","EA-B","EA-C","EA-D","Orb-A","Orb-B","Orb-C","Orb-D","ZAFT-A","ZAFT-B","ZAFT-C","ZAFT-D",
 "ZAFT-A","ZAFT-B","ZAFT-C","ZAFT-D"]
TABLES = [(0x8a1d368,SUIT),(0x8a1dd04,PILOT),(0x8a1da80,SHIP),(0x8a1db34,ENEMY),(0x8a1ddf0,CMDR),(0x8a1ded8,SOLDIER)]
# ranking default names (16-byte SJIS fields, in place)
# keyed by sha1 of the original Shift-JIS default name (the Japanese names are not stored)
RANKING = {'90797fc9d1a9ff3b1dcde2010b80c95a79aa9e37': 'Kira', '89eb24885205af5113f607df781865f7df42c5b1': 'Athrun', '393371aef5092c0b66755eaab6a8df12d52fccc1': 'Rau', '15f3cccaaccef0cc478074f9245d04f8287684d0': 'Mu', '0343fb3bcc17f53f4f4c4d0a73624bb626d9122b': 'Cagalli',
 '2d8ade5524d14987b1ae5c3b871a9150789ef3b5': 'Yzak', '2c9f7fa47792dd7b23722659d6207eaa4250b13f': 'Dearka', '77713f94d9788ba944147b756d02af0950d4e3bb': 'Nicol', '69b4a63ae6c774371a49b98eb300c0b4a6a70c5d': 'Shani', 'a901d803b5a4429b6d5eee5ecaed621820770435': 'Clotho'}
