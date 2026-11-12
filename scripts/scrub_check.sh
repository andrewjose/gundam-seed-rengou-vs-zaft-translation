#!/usr/bin/env bash
# Pre-publish check for this PUBLIC repository. Exits non-zero on any finding.
# Checks: Japanese/CJK characters in data or code, private paths / usernames / e-mail addresses,
# raw original-byte fields (orig_hex), files > 1 MB, game-file extensions, git author identities.
set -u
export LC_ALL=C.UTF-8 LANG=C.UTF-8   # grep -P needs a UTF-8 locale to see CJK code points
cd "$(dirname "$0")/.."
fail=0
say() { printf '%s\n' "$*"; }
hit() { say "FAIL: $1"; fail=1; }

# files that would be published: tracked + untracked-but-not-ignored
mapfile -t FILES < <(git ls-files --cached --others --exclude-standard | grep -v '^scripts/scrub_check.sh$')
[ ${#FILES[@]} -gt 0 ] || { say "no files?"; exit 2; }

# 1. CJK: hiragana/katakana, CJK punctuation, ideographs (incl. ext A), half/full-width forms.
#    Allowlist: none. (Code refers to such characters with \uXXXX escapes or hashes instead.)
out=$(printf '%s\0' "${FILES[@]}" | xargs -0 grep -nIP '[\x{3000}-\x{30FF}\x{3400}-\x{4DBF}\x{4E00}-\x{9FFF}\x{F900}-\x{FAFF}\x{FF00}-\x{FFEF}]' 2>/dev/null)
[ -z "$out" ] && say "ok   no CJK characters" || { hit "CJK characters:"; say "$out" | head -20; }

# 2. private paths and identities: any drive-letter path (except the system font folder), home / container /
#    session paths, plus optional private patterns (usernames, folder names) from the git-ignored file
#    scripts/scrub_private.txt (one extended regex per line) so they are never published themselves.
pat='[A-Za-z]:[\\/](Users|Projects|Downloads|[^W ]*ROMS?)|/home/[a-z]|/Users/[A-Za-z]|/mnt/|/sessions/|/root/|/tmp/'
out=$(printf '%s\0' "${FILES[@]}" | xargs -0 grep -nIiE "$pat" 2>/dev/null)
if [ -f scripts/scrub_private.txt ]; then
  priv=$(grep -v '^\s*$' scripts/scrub_private.txt | paste -sd'|' -)
  [ -n "$priv" ] && out="$out${out:+
}$(printf '%s\0' "${FILES[@]}" | xargs -0 grep -nIiE "$priv" 2>/dev/null)"
fi
[ -z "$out" ] && say "ok   no private paths/usernames" || { hit "private paths:"; say "$out" | head -20; }

# 3. e-mail addresses other than the GitHub no-reply / tool addresses
out=$(printf '%s\0' "${FILES[@]}" | xargs -0 grep -nIoE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' 2>/dev/null \
      | grep -vE '@users\.noreply\.github\.com$|noreply@anthropic\.com$')
[ -z "$out" ] && say "ok   no e-mail addresses" || { hit "e-mail addresses:"; say "$out" | head -20; }
out=$(printf '%s\0' "${FILES[@]}" | xargs -0 grep -nI '@gmail\.com' 2>/dev/null)
[ -z "$out" ] || { hit "@gmail.com found"; say "$out" | head; }

# 4. original bytes stored in patch data
out=$(printf '%s\0' "${FILES[@]}" | xargs -0 grep -nI 'orig_hex' 2>/dev/null)
[ -z "$out" ] && say "ok   no orig_hex fields" || { hit "orig_hex present:"; say "$out" | head; }

# 5. large files
big=$(for f in "${FILES[@]}"; do [ -f "$f" ] && [ "$(stat -c %s "$f" 2>/dev/null || stat -f %z "$f")" -gt 1048576 ] && echo "$f"; done)
[ -z "$big" ] && say "ok   no files > 1 MB" || { hit "files > 1 MB:"; say "$big"; }

# 6. game-file / derived-asset extensions
ext=$(printf '%s\n' "${FILES[@]}" | grep -iE '\.(iso|chd|cso|bin|elf|prx|gim|pmf|adx|at3|pmf|npy|pkl|png|bmp|tga|dds)$')
[ -z "$ext" ] && say "ok   no game-file extensions" || { hit "game-file extensions:"; say "$ext"; }

# 7. git identities
if git rev-parse --verify -q HEAD >/dev/null; then
  ids=$(git log --format='%an <%ae>%n%cn <%ce>' | sort -u | grep -vxF 'andrewjose <9953619+andrewjose@users.noreply.github.com>')
  [ -z "$ids" ] && say "ok   git author/committer identities" || { hit "unexpected git identities:"; say "$ids"; }
fi

[ $fail -eq 0 ] && say "scrub check PASSED" || say "scrub check FAILED"
exit $fail
