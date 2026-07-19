# Changelog

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
