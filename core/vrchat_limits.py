from __future__ import annotations

RANK_ORDER = ("EXCELLENT", "GOOD", "MEDIUM", "POOR", "VERY_POOR")

_SCORE_BANDS = {
    "EXCELLENT": (100.0, 81.0),
    "GOOD": (80.0, 61.0),
    "MEDIUM": (60.0, 41.0),
    "POOR": (40.0, 21.0),
    "VERY_POOR": (20.0, 0.0),
}

PC_LIMITS: dict[str, tuple[float, float, float, float]] = {
    "triangles": (32000, 70000, 70000, 70000),
    "materials": (4, 8, 16, 32),
    "skinned_meshes": (1, 2, 8, 16),
    "basic_meshes": (4, 8, 16, 24),
    "bones": (75, 150, 256, 400),
    "texture_mb": (40, 75, 110, 150),
}

QUEST_LIMITS: dict[str, tuple[float, float, float, float]] = {
    "triangles": (7500, 10000, 15000, 20000),
    "materials": (1, 1, 2, 4),
    "skinned_meshes": (1, 1, 2, 2),
    "basic_meshes": (1, 1, 2, 2),
    "bones": (75, 90, 150, 150),
    "texture_mb": (10, 18, 25, 40),
}

LIMITS_BY_PLATFORM = {
    "PC": PC_LIMITS,
    "QUEST": QUEST_LIMITS,
}

CATEGORY_LABELS = {
    "triangles": "Polygons",
    "materials": "Materials",
    "skinned_meshes": "Skinned Meshes",
    "basic_meshes": "Basic Meshes",
    "bones": "Bones",
    "texture_mb": "Texture Memory (MB)",
}

FIX_SUGGESTIONS = {
    "triangles": "Reduce polygon count",
    "materials": "Merge or remove duplicate materials",
    "skinned_meshes": "Join skinned meshes together",
    "basic_meshes": "Join or remove basic meshes",
    "bones": "Reduce bone count",
    "texture_mb": "Resize or compress textures",
}


def rank_for(value: float, thresholds: tuple[float, float, float, float]) -> str:
    excellent, good, medium, poor = thresholds
    if value <= excellent:
        return "EXCELLENT"
    if value <= good:
        return "GOOD"
    if value <= medium:
        return "MEDIUM"
    if value <= poor:
        return "POOR"
    return "VERY_POOR"


def category_score(value: float, thresholds: tuple[float, float, float, float]) -> tuple[str, float]:
    tier = rank_for(value, thresholds)
    excellent, good, medium, poor = thresholds
    bounds = {
        "EXCELLENT": (0.0, excellent),
        "GOOD": (excellent, good),
        "MEDIUM": (good, medium),
        "POOR": (medium, poor),
    }
    high, low = _SCORE_BANDS[tier]
    if tier == "VERY_POOR":
        span = poor if poor > 0 else 1.0
        fraction = min((value - poor) / span, 1.0)
        return tier, max(low - fraction * low, 0.0)

    lower, upper = bounds[tier]
    if upper <= lower:
        return tier, high
    fraction = (value - lower) / (upper - lower)
    fraction = min(max(fraction, 0.0), 1.0)
    return tier, high - fraction * (high - low)


def worst_rank(ranks: list[str]) -> str:
    worst_index = max(RANK_ORDER.index(rank) for rank in ranks)
    return RANK_ORDER[worst_index]
