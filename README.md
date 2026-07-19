# Ari's Avatar Toolkit

A modern avatar workflow toolkit for Blender 5.2 LTS.

Inspired by the long-unmaintained [Cats Blender Plugin](https://github.com/absolute-quantum/cats-blender-plugin), rebuilt from scratch for the current Blender Python API and the Extensions platform. No legacy code, no online services, no bundled third-party importers.

Source available: you can read the code and use the add-on freely, including for commercial avatar work. Modification and redistribution are not permitted. See [LICENSE.md](LICENSE.md).

## Features

### Fix Model in one click

- Translates Japanese bone, shape key, material, and object names. Fully offline, using a curated dictionary with kana romanization fallback. No Google Translate, no telemetry.
- Standardizes bone names from MMD, VRoid, Mixamo, Source Engine, and generic FBX rigs to the community-standard scheme (Hips, Spine, Left arm, Eye_L, and so on).
- Rebuilds a clean Hips, Spine, Chest, Neck, Head hierarchy and fixes the hips bone.
- Deletes zero-weight junk bones and merges their weights upward.
- Removes MMD rigid bodies, joints, and bone constraints.
- Applies transforms, normalizes armature modifiers, and joins meshes into a single Body mesh.

### Armature tools

- Attach Mesh (Auto Weights): parents any mesh to the armature and generates automatic bone-heat weights in one click.
- Remove End Bones: deletes leftover end bones (_end, _end_end, _End.001, and similar) in one click, merging their weights into the parents.
- Merge Weights to Parent for any selected bones, in edit or pose mode.
- Remove zero-weight bones, delete bones by pattern, remove all constraints.

### Pose tools

- Start and stop pose mode from the panel.
- Apply as Rest Pose that also works on meshes with shape keys, which Blender cannot do natively.

### Clothing and weights

- Elastic Fit: pushes clothing meshes out of the body with an elastic falloff. UV and topology safe, and shape keys are carried along. Supports a per-region offset group for areas that need extra clearance and a pin group for vertices that must never move.
- Robust Weight Transfer: transfers bone weights from the body to clothing using confident surface matching plus diffusion inpainting for uncertain areas such as armpits, chest, and between the legs. No manual weight smoothing needed. Original implementation of the SIGGRAPH Asia 2023 paper "Robust Skin Weights Transfer via Weight Inpainting" (Abdrashitov et al.).

### Visemes

- Generates the 15 standard vrc.v_* visemes from your A, O, and CH mouth shapes, with adjustable intensity.

### Eye tracking

- Sets up Eye_L and Eye_R bones for modern bone-based eye tracking: renaming, Head parenting, upright orientation, plus test and reset rotation buttons.

### Decimation

- Global triangle budget distributed proportionally across meshes.
- Safe mode never touches meshes with shape keys. Selected and Full modes are available when you need them.

### Shape keys

- Smooth Shape Keys: relaxes shape key deltas to fix jagged or crunchy deformation, with adjustable strength, an optional vertex mask, and optional backup copies of the originals.
- Apply shape key to basis, with a reverted key kept for toggling back.
- Remove empty shape keys, sort visemes to the top of the list.

### Mesh and materials

- Join and separate meshes, shape-key-aware merge doubles.
- Merge duplicate .001-style materials, remove unused material slots.

## Comparison with Cats

| | Cats Blender Plugin | Ari's Avatar Toolkit |
|---|---|---|
| Blender support | 2.79 to 3.6 (abandoned) | 5.2 LTS |
| Packaging | Legacy add-on (bl_info) | Blender Extension (blender_manifest.toml) |
| Translation | Google Translate (online) | Offline dictionary, private and deterministic |
| Importers | Bundled forks of mmd_tools and others | Uses official importers, no stale bundled code |
| Eye tracking | Legacy shape-key based | Modern bone-based |
| Clothing tools | None | Elastic fit and robust weight transfer |
| Codebase | Ten years of accumulated patches | Clean, modular Python |

## Installation

1. Download the latest ari_avatar_toolkit zip from the [Releases](https://github.com/yoisthatari/Ari-s-Avatar-Toolkit/releases) page.
2. In Blender 5.2, open Edit, Preferences, Get Extensions, click the dropdown arrow in the top right corner, and choose Install from Disk. Pick the zip.
3. The panel appears in the 3D View sidebar (N key) under Ari's Toolkit.

## Quick start

1. Import your model. Use the official mmd_tools extension for PMX, the VRM add-on for VRM, or the built-in FBX importer.
2. Pick the armature at the top of the panel (auto-detected if there is only one) and click Fix Model.
3. Set up Visemes and Eye Tracking.
4. Fit clothing and transfer weights from the Clothing and Weights panel if you are assembling an outfit.
5. Decimate if you are over your target platform's polygon budget.
6. Export FBX and bring it into Unity.

## Building from source

Run from the repository root:

```
blender --command extension build
```

The zip is written next to the manifest.

## License

Source available, no derivatives, no redistribution. See [LICENSE.md](LICENSE.md). This add-on is distributed only through this repository and its Releases page, not on the Blender Extensions Platform.

Cats Blender Plugin is a separate project (MIT licensed) and no code from it is used here. The feature set and workflow are modeled after it. Thanks to its authors for a decade of avatar tooling.

The weight transfer feature is an independent implementation of "Robust Skin Weights Transfer via Weight Inpainting" by Rinat Abdrashitov, Kim Raichstat, Jared Monsen, and David Hill (SIGGRAPH Asia 2023). Please cite the paper when using it in academic work.
