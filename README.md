# Ari's Avatar Toolkit

A modern, optimized avatar workflow toolkit for **Blender 5.2 LTS**.

Inspired by the legendary (and long-unmaintained) [Cats Blender Plugin](https://github.com/absolute-quantum/cats-blender-plugin),
rebuilt **from scratch** for the current Blender Python API and the
Extensions platform — no legacy code, no online services, no bundled
third-party importers.

> **Source-available:** you can read the code and use the add-on freely
> (including for commercial avatar work), but modification and
> redistribution are not permitted. See [LICENSE.md](LICENSE.md).

## Features

### 🔧 Fix Model — one click
- Translates Japanese bone / shape key / material / object names
  (fully **offline** — curated dictionary + kana romanization, no Google
  Translate, no telemetry)
- Standardizes bone names from **MMD, VRoid, Mixamo, Source Engine and
  generic FBX** rigs to the community-standard scheme
  (`Hips`, `Spine`, `Left arm`, `Eye_L`, …)
- Rebuilds a clean `Hips → Spine → Chest → Neck → Head` hierarchy and fixes
  the hips bone
- Deletes zero-weight junk bones and merges their weights upward
- Removes MMD rigid bodies, joints, and bone constraints
- Applies transforms, normalizes armature modifiers, joins meshes into a
  single `Body`

### 🦴 Armature tools
- **Merge Weights to Parent** for any selected bones (edit or pose mode)
- Remove zero-weight bones, delete bones by regex pattern
- Shape-key-safe **Apply as Rest Pose** (Blender can't do this natively on
  meshes with shape keys)

### 👄 Visemes
- Generates the 15 standard `vrc.v_*` visemes from your A / O / CH mouth
  shapes, with adjustable intensity

### 👀 Eye tracking
- Sets up `Eye_L` / `Eye_R` bones for modern bone-based eye tracking:
  renaming, Head parenting, upright orientation, plus test/reset rotation

### 👕 Clothing & weights
- **Elastic Fit**: pushes clothing meshes out of the body with an elastic
  falloff — UV and topology safe, shape keys carried along
- **Robust Weight Transfer**: body-to-clothing bone weights via confident
  surface matching plus diffusion inpainting for problem areas (armpits,
  chest, between legs) — no manual weight smoothing needed. Original
  implementation of the SIGGRAPH Asia 2023 paper *Robust Skin Weights
  Transfer via Weight Inpainting* (Abdrashitov et al.)

### 📉 Decimation
- Global triangle budget distributed proportionally across meshes
- **Safe mode** never touches meshes with shape keys; Selected and Full
  modes available when you need them

### 🎭 Shape keys, meshes & materials
- Apply shape key to basis (with reverted key), smooth shape key deltas
  (with optional vertex mask), remove empty shape keys, sort visemes to
  the top
- Join / separate meshes, shape-key-aware merge doubles
- Merge duplicate `.001`-style materials, remove unused material slots

## What's different from Cats?

| | Cats Blender Plugin | Ari's Avatar Toolkit |
|---|---|---|
| Blender support | 2.79 – 3.6 (abandoned) | **5.2 LTS** |
| Packaging | Legacy add-on (`bl_info`) | **Blender Extension** (`blender_manifest.toml`) |
| Translation | Google Translate (online) | **Offline dictionary** — private & deterministic |
| Importers | Bundled forks of mmd_tools etc. | Uses official importers/extensions — no stale bundled code |
| Eye tracking | Legacy shape-key based | Modern bone-based |
| Codebase | ~10 yrs of accumulated patches | Clean, typed, modular Python |

## Installation

1. Download the latest `ari_avatar_toolkit-x.y.z.zip` from
   [Releases](https://github.com/yoisthatari/Ari-s-Avatar-Toolkit/releases)
   (or *Code ▸ Download ZIP*).
2. In Blender 5.2: `Edit ▸ Preferences ▸ Get Extensions ▸ ⌄ (top-right) ▸
   Install from Disk…` and pick the zip.
3. The panel appears in the 3D View sidebar (`N` key) under
   **Ari's Toolkit**.

## Typical workflow

1. Import your model (PMX via the official mmd_tools extension, VRM via the
   VRM add-on, or FBX).
2. Pick the armature at the top of the panel (auto-detected if there's only
   one) and hit **Fix Model**.
3. Set up **Visemes** and **Eye Tracking**.
4. **Decimate** if you're over your target platform's polygon budget.
5. Export FBX and bring it into Unity.

## Building from source

```
blender --command extension build
```

Run from the repository root; the zip lands next to it.

## License

Source-available, no derivatives, no redistribution —
see [LICENSE.md](LICENSE.md). This add-on is distributed only through this
repository and its Releases page, not on the Blender Extensions Platform.

Cats Blender Plugin is a separate project (MIT licensed); no code from it
is used here. Feature set and workflow are lovingly modeled after it —
thank you to its authors for a decade of avatar tooling.
