# Changelog

## 1.1.0 — 2026-07-19

- **Elastic Clothing Fit**: pushes clothing out of the body with an elastic
  falloff — UV and topology safe, shape keys carried along
- **Robust Weight Transfer**: body-to-clothing weight transfer using
  confident surface matches plus diffusion inpainting for uncertain areas
  (based on the SIGGRAPH Asia 2023 paper "Robust Skin Weights Transfer via
  Weight Inpainting" by Abdrashitov et al.)
- **Smooth Shape Keys**: relaxes shape key deltas to fix jagged or crunchy
  deformation, with optional vertex group mask
- New "Clothing & Weights" panel

## 1.0.0 — 2026-07-19

Initial release, built for Blender 5.2 LTS.

- One-click **Fix Model**: offline name translation, bone name
  standardization (MMD / VRoid / Mixamo / Source / FBX), hierarchy repair,
  zero-weight bone cleanup with upward weight merging, constraint and MMD
  rigid body removal, transform application, mesh joining
- Armature tools: merge weights to parent, remove zero-weight bones,
  delete bones by pattern, remove constraints
- Pose tools: start/stop pose mode, shape-key-safe apply as rest pose
- Viseme generator (15 standard `vrc.v_*` shapes from A/O/CH)
- Bone-based eye tracking setup with test rotation
- Budget-based decimation with shape key protection
- Shape key utilities: apply to basis, remove empty, sort
- Mesh & material utilities: join/separate, merge doubles, merge duplicate
  materials, remove unused slots
