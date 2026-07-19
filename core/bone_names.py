from __future__ import annotations

import re

_PREFIX_REPLACEMENTS = (
    ("mixamorig:", ""),
    ("mixamorig_", ""),
    ("valvebiped.bip01_", ""),
    ("valvebiped.bip02_", ""),
    ("bip01_", ""),
    ("bip02_", ""),
    ("bip_", ""),
    ("b_", ""),
    ("j_bip_c_", ""),
    ("j_bip_l_", "left_"),
    ("j_bip_r_", "right_"),
    ("j_adj_", ""),
    ("def-", ""),
    ("def_", ""),
)

_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")

_SIDE_LEFT = "left"
_SIDE_RIGHT = "right"

_CENTRAL_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"^(hips?|hip|pelvis|下半身|腰|lowerbody|lower_body|waist)$", "Hips"),
    (r"^(spine|上半身|upperbody|upper_body|torso|abdomen)$", "Spine"),
    (r"^(chest|上半身2|upper_?body_?2|spine1|spine_01)$", "Chest"),
    (r"^(upper_?chest|上半身3|upper_?body_?3|spine[23]|spine_0[23])$", "Upper Chest"),
    (r"^(neck|首|neck1)$", "Neck"),
    (r"^(head|頭|face_root)$", "Head"),
)

_SIDED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"^(shoulder|clavicle|肩|collar(bone)?)$", "shoulder"),
    (r"^(upper_?arm|arm|腕|uparm|bicep)$", "arm"),
    (r"^(fore_?arm|elbow|lower_?arm|ひじ|肘|loarm)$", "elbow"),
    (r"^(hand|wrist|手首|手)$", "wrist"),
    (r"^(upper_?leg|thigh|leg|足|脚|太もも|uple?g)$", "leg"),
    (r"^(lower_?leg|calf|knee|shin|ひざ|膝|foreleg)$", "knee"),
    (r"^(foot|ankle|足首|feet)$", "ankle"),
    (r"^(toe(s|base|0)?|つま先|足先)$", "toe"),
    (r"^(eye|目)$", "eye"),
)

_FINGER_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"thumb|親指", "Thumb"),
    (r"index|人差し?指|ind", "IndexFinger"),
    (r"middle|中指|mid", "MiddleFinger"),
    (r"ring|薬指", "RingFinger"),
    (r"little|pinkie|pinky|小指", "LittleFinger"),
)

_SIDED_STANDARD = {
    "shoulder": "{side} shoulder",
    "arm": "{side} arm",
    "elbow": "{side} elbow",
    "wrist": "{side} wrist",
    "leg": "{side} leg",
    "knee": "{side} knee",
    "ankle": "{side} ankle",
    "toe": "{side} toe",
}

_EYE_STANDARD = {_SIDE_LEFT: "Eye_L", _SIDE_RIGHT: "Eye_R"}


def _normalize(name: str) -> str:
    text = name.strip().lower()
    text = text.replace("　", " ").translate(_FULLWIDTH_DIGITS)
    for prefix, replacement in _PREFIX_REPLACEMENTS:
        if text.startswith(prefix):
            text = replacement + text[len(prefix):]
            break
    text = re.sub(r"[\s\-.]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def _extract_side(text: str) -> tuple[str, str | None]:
    for jp, side in (("左", _SIDE_LEFT), ("右", _SIDE_RIGHT)):
        if jp in text:
            return text.replace(jp, ""), side

    patterns = (
        (r"^(left|l)_(.+)$", _SIDE_LEFT, 2),
        (r"^(right|r)_(.+)$", _SIDE_RIGHT, 2),
        (r"^(.+)_(left|l)$", _SIDE_LEFT, 1),
        (r"^(.+)_(right|r)$", _SIDE_RIGHT, 1),
        (r"^left(.+)$", _SIDE_LEFT, 1),
        (r"^right(.+)$", _SIDE_RIGHT, 1),
    )
    for pattern, side, group in patterns:
        match = re.match(pattern, text)
        if match:
            return match.group(group).strip("_"), side
    return text, None


def _match_finger(base: str, side: str) -> str | None:
    match = re.match(r"^(.*?)_?(\d+)$", base)
    stem, segment = (match.group(1), match.group(2)) if match else (base, "0")

    for pattern, standard in _FINGER_PATTERNS:
        if re.search(pattern, stem):
            suffix = "_L" if side == _SIDE_LEFT else "_R"
            return f"{standard}{int(segment)}{suffix}"
    return None


def standard_bone_name(name: str) -> str | None:
    text = _normalize(name)
    if not text:
        return None

    for pattern, standard in _CENTRAL_PATTERNS:
        if re.match(pattern, text):
            return standard

    base, side = _extract_side(text)
    if side is None:
        return None

    finger = _match_finger(base, side)
    if finger:
        return finger

    for pattern, standard in _SIDED_PATTERNS:
        if re.match(pattern, base):
            if standard == "eye":
                return _EYE_STANDARD[side]
            side_word = "Left" if side == _SIDE_LEFT else "Right"
            return _SIDED_STANDARD[standard].format(side=side_word)
    return None


def build_rename_map(bone_names: list[str]) -> dict[str, str]:
    taken = set(bone_names)
    result: dict[str, str] = {}
    claimed: set[str] = set()
    for name in bone_names:
        standard = standard_bone_name(name)
        if standard is None or standard == name:
            continue
        if standard in claimed or (standard in taken and standard != name):
            continue
        result[name] = standard
        claimed.add(standard)
    return result
