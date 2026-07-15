"""
SilentXForward/caption.py
──────────────────────────
Custom Caption Engine.

Features:
  1. Variable extraction from filename/caption (title, year, season, episode,
     quality, resolution, audio, codec, ott, fps, bitrate, language, sub,
     file_size, duration, height, width, file_name, default_caption, extension)
  2. Word Replace  — "Old:New" rules, applied before variable extraction.
  3. Word Remove   — words stripped out before variable extraction.
  4. Caption Template rendering — {variable} tokens replaced with real values.

Kept as a separate file (like caption.py in other projects) so helper.py /
forward.py don't get bloated — file/folder structure elsewhere is untouched.
"""

import re

# ==================== REGEX PATTERNS ====================

_YEAR_RE       = re.compile(r"\b(19\d{2}|20\d{2})\b")
_SEASON_EP_RE  = re.compile(r"\bS(\d{1,2})\s?E(\d{1,4})\b", re.I)
_SEASON_RE     = re.compile(r"\b(?:S(?:eason)?\s?)(\d{1,2})\b", re.I)
_EPISODE_RE    = re.compile(r"\b(?:E(?:p(?:isode)?)?\s?)(\d{1,4})\b", re.I)
_RESOLUTION_RE = re.compile(r"\b(480p|540p|576p|720p|900p|1080p|1440p|2160p|4k)\b", re.I)
_QUALITY_RE    = re.compile(
    r"\b(HDRip|BRRip|BDRip|BluRay|BD|WEB[-\s]?DL|WEBRip|HDTV|HDTS|HDCAM|"
    r"CAMRip|PreDVD|DVDScr|DVDRip)\b", re.I
)
_AUDIO_RE      = re.compile(
    r"\b(DDP?\s?7\.1|DDP?\s?5\.1|DDP?\s?2\.0|DD\s?5\.1|DD\s?2\.0|"
    r"AAC(?:\d(?:\.\d)?)?|AC-?3|Atmos|TrueHD|Dual[-\s]?Audio|Multi[-\s]?Audio)\b", re.I
)
_CODEC_RE      = re.compile(r"\b(x264|x265|H\.?264|H\.?265|HEVC|AVC|AV1)\b", re.I)
_OTT_RE        = re.compile(
    r"\b(NF|Netflix|AMZN|Amazon|Hotstar|ZEE5|SonyLIV|SunNXT|DSNP|Disney\+?|"
    r"ATVP|AppleTV|JioCinema|MX|Voot)\b", re.I
)
_FPS_RE        = re.compile(r"\b(\d{2,3})\s?FPS\b", re.I)
_BITRATE_RE    = re.compile(r"\b(\d{2,5})\s?kbps\b", re.I)
_SHORTSUB_RE   = re.compile(r"\b(Msub|Esub|Multi[-\s]?Sub)\b", re.I)
_LANGUAGE_WORDS = [
    "Hindi", "English", "Tamil", "Telugu", "Malayalam", "Kannada", "Bengali",
    "Punjabi", "Marathi", "Gujarati", "Urdu", "Multi", "Hin", "Eng",
]
_LANGUAGE_RE = re.compile(r"\b(" + "|".join(_LANGUAGE_WORDS) + r")\b", re.I)

_ALL_MARKER_PATTERNS = [
    _SEASON_EP_RE, _YEAR_RE, _SEASON_RE, _EPISODE_RE, _RESOLUTION_RE,
    _QUALITY_RE, _AUDIO_RE, _CODEC_RE, _OTT_RE, _FPS_RE, _BITRATE_RE,
    _SHORTSUB_RE,
]

VARIABLE_LIST = [
    "file_name", "default_caption", "title", "file_size", "duration",
    "language", "audio", "quality", "resolution", "year", "season",
    "episode", "ott", "lib", "extension", "fps", "bitrate", "shortsub",
    "height", "width",
]


# ==================== HUMAN-READABLE HELPERS ====================

def human_size(num_bytes) -> str:
    if not num_bytes:
        return ""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def human_duration(seconds) -> str:
    if not seconds:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ==================== WORD REMOVE / REPLACE ====================

def apply_remove_words(text: str, words: list) -> str:
    if not text or not words:
        return text
    for w in words:
        if not w:
            continue
        text = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", "", text, flags=re.I)
    return re.sub(r"\s{2,}", " ", text).strip(" ._-")


def apply_replacements(text: str, rules: list) -> str:
    if not text or not rules:
        return text
    for old, new in rules:
        if not old:
            continue
        text = re.sub(r"(?<!\w)" + re.escape(old) + r"(?!\w)", new, text, flags=re.I)
    return re.sub(r"\s{2,}", " ", text).strip()


# ==================== VARIABLE EXTRACTION ====================

def _search_both(pattern, primary, secondary):
    """Pehle primary text (usually filename) mein dhundo, na mile to secondary (caption) mein."""
    m = pattern.search(primary)
    if m:
        return m
    return pattern.search(secondary)


def _extract_title(working_primary: str) -> str:
    """Sabse pehla marker (year/season/quality/etc) se pehle wala part = title."""
    cut_at = len(working_primary)
    for pattern in _ALL_MARKER_PATTERNS:
        m = pattern.search(working_primary)
        if m and m.start() < cut_at:
            cut_at = m.start()
    title = working_primary[:cut_at]
    title = re.sub(r"[.\-_]+", " ", title)
    title = re.sub(r"\s{2,}", " ", title).strip(" -._")
    return title


def extract_variables(message, replace_rules=None, remove_words=None) -> dict:
    """Message (video/document/audio/animation) se saare caption-variables nikalta hai."""
    media = (
        getattr(message, "document", None) or getattr(message, "video", None) or
        getattr(message, "audio", None) or getattr(message, "animation", None)
    )
    file_name = getattr(media, "file_name", "") or "" if media else ""
    default_caption = message.caption or message.text or ""

    # ✅ FIX: sirf underscore ko space karo, DOT ko preserve rakho — warna "DDP5.1",
    # "x264" jaisi numeric/version patterns (jinme dot zaroori hai) toot jaate hain.
    # Title nikaalte waqt hi dot ko space mein convert karenge.
    working_primary   = (file_name or "").replace("_", " ")
    working_secondary = (default_caption or "").replace("_", " ")

    # ✅ FIX: remove/replace words dono sources pe apply karo
    working_primary   = apply_remove_words(working_primary, remove_words or [])
    working_primary   = apply_replacements(working_primary, replace_rules or [])
    working_secondary = apply_remove_words(working_secondary, remove_words or [])
    working_secondary = apply_replacements(working_secondary, replace_rules or [])

    default_caption_clean = apply_replacements(
        apply_remove_words(default_caption, remove_words or []), replace_rules or []
    )

    # ✅ FIX: agar filename missing hai to secondary(caption) hi primary ban jaaye,
    # taaki title bhi usi se nikle
    if not working_primary:
        working_primary, working_secondary = working_secondary, ""

    variables = {v: "" for v in VARIABLE_LIST}
    variables["file_name"] = file_name
    variables["default_caption"] = default_caption_clean

    se_match = _search_both(_SEASON_EP_RE, working_primary, working_secondary)
    if se_match:
        variables["season"]  = f"S{int(se_match.group(1)):02d}"
        variables["episode"] = f"E{int(se_match.group(2)):02d}"
    else:
        sm = _search_both(_SEASON_RE, working_primary, working_secondary)
        if sm:
            variables["season"] = f"S{int(sm.group(1)):02d}"
        em = _search_both(_EPISODE_RE, working_primary, working_secondary)
        if em:
            variables["episode"] = f"E{int(em.group(1)):02d}"

    ym = _search_both(_YEAR_RE, working_primary, working_secondary)
    if ym:
        variables["year"] = ym.group(1)

    rm = _search_both(_RESOLUTION_RE, working_primary, working_secondary)
    if rm:
        variables["resolution"] = rm.group(1).lower()

    qm = _search_both(_QUALITY_RE, working_primary, working_secondary)
    if qm:
        variables["quality"] = qm.group(1)

    am = _search_both(_AUDIO_RE, working_primary, working_secondary)
    if am:
        variables["audio"] = am.group(1)

    cm = _search_both(_CODEC_RE, working_primary, working_secondary)
    if cm:
        variables["lib"] = cm.group(1)

    om = _search_both(_OTT_RE, working_primary, working_secondary)
    if om:
        variables["ott"] = om.group(1)

    fm = _search_both(_FPS_RE, working_primary, working_secondary)
    if fm:
        variables["fps"] = f"{fm.group(1)}FPS"

    bm = _search_both(_BITRATE_RE, working_primary, working_secondary)
    if bm:
        variables["bitrate"] = f"{bm.group(1)}kbps"

    smb = _search_both(_SHORTSUB_RE, working_primary, working_secondary)
    if smb:
        variables["shortsub"] = smb.group(1)

    lm = _search_both(_LANGUAGE_RE, working_primary, working_secondary)
    if lm:
        variables["language"] = lm.group(1)

    variables["title"] = _extract_title(working_primary)

    if "." in file_name:
        variables["extension"] = file_name.rsplit(".", 1)[-1]

    video = getattr(message, "video", None)
    if video:
        variables["height"]   = str(getattr(video, "height", "") or "")
        variables["width"]    = str(getattr(video, "width", "") or "")
        variables["duration"] = human_duration(getattr(video, "duration", None))
    elif getattr(message, "audio", None):
        variables["duration"] = human_duration(getattr(message.audio, "duration", None))

    file_size = getattr(media, "file_size", None) if media else None
    variables["file_size"] = human_size(file_size)

    return variables


def render_caption(template: str, variables: dict) -> str:
    def _sub(m):
        return str(variables.get(m.group(1), ""))
    text = re.sub(r"\{(\w+)\}", _sub, template)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def build_final_caption(message, caption_template: str = "", endtext: str = "",
                         replace_rules=None, remove_words=None) -> str:
    """Full pipeline: remove words -> replace words -> extract vars -> template/default -> +endtext."""
    variables = extract_variables(message, replace_rules=replace_rules, remove_words=remove_words)

    if caption_template:
        base = render_caption(caption_template, variables)
    else:
        base = variables.get("default_caption", "")

    if endtext:
        base = f"{base}\n\n{endtext}".strip() if base else endtext

    return base
