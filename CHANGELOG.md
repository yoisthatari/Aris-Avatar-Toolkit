# Changelog

## 1.1.0 (2026-07-19)

- Import Model: one-click import for PMX/PMD (through the official MMD
  Tools extension), VRM, FBX, glTF, OBJ, STL and Collada, with automatic
  armature selection
- Install MMD Tools: installs the official extension from
  extensions.blender.org through Blender's extension system
- Export Model: FBX export with avatar-safe settings (shape keys kept,
  no leaf bones, embedded textures, triangle count warning)
- Blendshape transfer: moves shape keys between meshes with different
  topology, with subdivision and displace pre-processing (preview
  toggles included) and a paintable red/blue transfer mask
- Elastic Clothing Fit: pushes clothing out of the body with an elastic
  falloff. UV and topology safe, shape keys carried along. Per-region
  offset groups and pin groups supported
- Robust Weight Transfer: body-to-clothing weight transfer using
  confident surface matches plus diffusion inpainting for uncertain areas
  (based on the SIGGRAPH Asia 2023 paper "Robust Skin Weights Transfer via
  Weight Inpainting" by Abdrashitov et al.)
- Smooth Shape Keys: relaxes shape key deltas to fix jagged or crunchy
  deformation, with optional vertex mask and backup copies
- Attach Mesh (Auto Weights): one-click parenting with automatic
  bone-heat weights
- Remove End Bones: one-click cleanup of leftover _end bones
- New Clothing and Weights panel
- Vertex/Face Alignment: aligns the selected objects to a vertex or face
  center picked on the active object in edit mode, with a new Align Tools
  panel
- Avatar Analyzer: scores an avatar against VRChat's PC and Quest
  performance rank thresholds, with heavy-mesh and texture-hotspot
  reports, a JSON export, and creator tools (Texture Optimizer, Mesh
  Heatmap, Auto Fix Avatar with undo, Restore Texture Size Backup,
  scene-wide Batch Report)
- Blendshape Sync: keeps a shape key active by name across the active
  object, an Auxiliary object, and every selected mesh, with a Quick
  Sculpt Mode shortcut and an instant reset

## 1.0.0 (2026-07-19)

Initial release, built for Blender 5.2 LTS.

- One-click Fix Model: offline name translation, bone name
  standardization (MMD, VRoid, Mixamo, Source, FBX), hierarchy repair,
  zero-weight bone cleanup with upward weight merging, constraint and MMD
  rigid body removal, transform application, mesh joining
- Armature tools: merge weights to parent, remove zero-weight bones,
  delete bones by pattern, remove constraints
- Pose tools: start and stop pose mode, shape-key-safe apply as rest pose
- Viseme generator (15 standard vrc.v_* shapes from A, O, CH)
- Bone-based eye tracking setup with test rotation
- Budget-based decimation with shape key protection
- Shape key utilities: apply to basis, remove empty, sort
- Mesh and material utilities: join and separate, merge doubles, merge
  duplicate materials, remove unused slots
