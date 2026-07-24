# Changelog

## 1.6.1 (2026-07-23)

### Fixed

- Avatar Doctor wrongly reported humanoid bones as missing on any rig that
  did not already use the toolkit's own naming. A rig with Arm_L, Elbow_L
  and Wrist_L was told twelve bones were absent when every one of them was
  present. The check now runs bone names through the same standardizer the
  rest of the toolkit uses, so Arm_L is recognised as Left arm
- Rigs whose bones are all present but not yet standardized now get a
  gentle note instead of a red error, since nothing is actually wrong
- Mixamo rigs never produced a knee bone. Mixamo calls the thigh UpLeg and
  the shin Leg, and both were being read as the upper leg, so Left knee and
  Right knee could never be matched and Fix Model quietly left the shin
  unrenamed. Mixamo names are now mapped with their own scheme
- Counts read correctly in the singular: "1 mesh", "1 problem to fix"

## 1.6.0 (2026-07-23)

- The sidebar is reorganised around the actual workflow. Top-level panels
  drop from eighteen to ten, with related tools folded in as sub-panels
  instead of sitting side by side in one long wall
- Shape key tools are finally together. Transfer Between Meshes, Sync
  Across Meshes and Batch Creator now live under Shape Keys, rather than
  being scattered with Decimation sitting in the middle of them
- Attach & Merge Parts moved under Clothing & Weights, so the body mesh it
  needs is set right above it instead of being duplicated
- Translation and the pose tools moved under Model, and the pose buttons
  got their own sub-panel so the Model panel stays short
- Weight Tools split out of Avatar Doctor into its own sub-panel, so the
  check-up results are no longer buried under a wall of buttons
- Visemes and Eye Tracking sit under Armature; Align Tools and the Vertex
  Error Selector sit under Mesh & Materials
- Every panel now declares an explicit order, so the layout no longer
  depends on the order things happen to be registered in
- Settings use Blender's aligned two-column property layout, and long help
  text wraps instead of being cut off at the panel edge
- The Model panel shows a mesh and bone count at a glance
- Layout verified by rendering the real sidebar and reading it back, which
  caught several things that compile and run perfectly well but look wrong:
  checkbox labels being cut off ("Remove Zero-Weig...", "Transfer Weights
  ..."), the Safe/Selected/Full and Face Count/Ratio buttons stacking into
  a tall column instead of one row, and counts reading "1 meshes"

## 1.5.0 (2026-07-23)

- Avatar Doctor: a full pre-Unity check-up in one click, with results grouped
  by severity and a fix button beside everything it can mend. Checks for
  unweighted vertices, vertices riding more than four bones, unnormalized
  weights, missing humanoid bones, unapplied transforms, loose and
  zero-area geometry, missing UVs, empty material slots, triangle budget,
  non-manifold edges, ngons and bone count. See docs/avatar-doctor.md
- Limit Bone Influences: keeps only the strongest bones on each vertex and
  renormalizes. Unity keeps four per vertex and silently drops the rest, so
  this is the only way to see in Blender what the avatar will really do
- Fix Unweighted Vertices: stranded vertices borrow the weights of their
  nearest weighted neighbour, which clears Unity's unweighted vertex error
- Normalize Weights, Select Unweighted and Remove Loose Geometry
- Fix Weights runs the three weight repairs together in the right order
- Every weight tool touches bone groups only, so mask, pin and offset
  groups are never disturbed

## 1.4.0 (2026-07-23)

- Hide Body Under Clothing: finds the body geometry sitting under the
  selected garments and masks it away, so nothing pokes through and the
  hidden polygons stop costing you. It uses a Mask modifier, so it is fully
  reversible with Show Body Again and shape keys are untouched
- Elastic Fit gained a Search Distance, so a stray vertex can no longer
  snap across to the far side of a limb, and configurable Fit Passes for
  stubborn clipping
- Quad Remesh (Retopology): rebuilds a mesh into clean quads with
  Blender's built-in QuadriFlow field-aligned remesher, then transfers the
  bone weights back onto the new topology with the robust inpainting method
  and reconnects the armature. Symmetry, boundary and sharp-edge options
  included. Meshes with shape keys are skipped by default, since a remesh
  cannot preserve them. See docs/quad-remesh.md
- The Decimation panel is now Decimation & Retopology, with the triangle
  budget and the remesher side by side
- Weight transfer logic is now shared, so the remesher and the clothing
  tools use the same tested code path

## 1.3.0 (2026-07-23)

- Attach & Merge panel for building an avatar from separately sold parts
- Merge Armatures: attach a part that came with its own armature (a head
  sold separately, or clothing shipped with a matching rig) onto the base.
  Bones are fused by name (exact and standardized), any extra bones the
  attachment adds are kept and reparented in place, meshes move onto the
  base armature with their weights remapped, and the leftover armature is
  removed
- Attach Mesh-Only: one-click flow for attachments that are just a mesh
  with no armature, parenting to the base and transferring body weights
  with an optional elastic fit pass first
- Import Attachment shortcut in the new panel
- New Substance Painter & Unity panel for the full texturing round trip
- Prep for Painter: one click to give every material a clean ASCII texture
  set name (Japanese names go through the offline dictionary first), drop
  unused material slots, settle the bind pose, and warn about meshes with
  no UVs
- Export for Painter: FBX with triangles, tangent space, metre scale and
  Y-up, which is what Painter bakes against and Unity imports cleanly
- Import Painted Textures: point it at Painter's export folder and it
  matches each file to its material and wires the Principled BSDF, including
  unpacking Unity's MetallicSmoothness (red to Metallic, alpha inverted to
  Roughness) and AlbedoTransparency. Re-importing replaces rather than
  duplicates, and DirectX normal maps are flagged
- Fix Colour Spaces: corrects every texture to sRGB or Non-Colour based on
  what it feeds, fixing the classic flat or washed-out look in Unity

### Fixed

- Shapekey Batch Creator was unreachable: its `batch_shapekey_names` and
  `batch_page` settings were never defined, so the operators raised an
  error, and no panel ever showed them. Settings added and the panel now
  includes the paginated, clickable shape key browser the docs describe
- Vertex Error Selector was unreachable for the same reason: its
  `vertex_error_input` setting was missing and it had no panel. Both added,
  in a new Vertex Tools panel
- Store Pose, Restore Pose and Reset Pose worked but had no buttons
  anywhere in the UI; they now sit under the pose controls in the Model
  panel
- All 66 operators are now reachable from the sidebar

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
