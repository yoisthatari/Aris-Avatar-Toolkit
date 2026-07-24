# Avatar Doctor

A full check-up before your avatar goes to Unity, with a one-click fix beside everything that can be mended.

Click **Check Avatar Health** and the results appear grouped by severity: red things will stop the upload, orange things will look wrong, grey things are just worth knowing.

## What it checks

| Check | Level | Why it matters |
| --- | --- | --- |
| Unweighted vertices | Error | Unity refuses the mesh and VRChat rejects the avatar |
| Missing humanoid bones | Error | Unity cannot build a humanoid rig without them |
| Unapplied transforms | Error | The avatar imports at the wrong size or lying on its side |
| Vertices over 4 bones | Warning | Unity keeps only the strongest 4, so posing differs from Blender |
| Unnormalized weights | Warning | Limbs shrink or drift when the avatar moves |
| Loose vertices | Warning | Export as junk, and are the usual cause of unweighted vertex errors |
| Zero-area faces | Warning | Break normal map bakes and confuse remeshers |
| Meshes without UVs | Warning | Cannot be textured or painted |
| Empty material slots | Warning | Become missing materials in Unity |
| Over 70,000 triangles | Warning | Above VRChat's guidance for a Good rank |
| Non-manifold edges | Info | Fine for rendering, but Quad Remesh needs clean geometry |
| Ngons | Info | Unity triangulates them anyway, but they can shade oddly |
| High bone count | Info | Costs performance rank in VRChat |

## Weight Tools

These act on your selected meshes, or the whole model if nothing is selected.

**Fix Weights** runs the three repairs below in the right order, which is usually all you need.

- **Fix Unweighted Vertices** — finds vertices with no bone weight and borrows the weights of their nearest weighted neighbour. This is what clears Unity's unweighted vertex error.
- **Limit Bone Influences** — keeps only the strongest bones on each vertex and renormalizes what is left. Unity keeps 4 per vertex and silently drops the rest, so a model that looks right in Blender can deform differently in game. Running this makes Blender show you the truth.
- **Normalize Weights** — makes each vertex's weights add up to exactly 1.0.
- **Select Unweighted** — jumps into Edit Mode with the problem vertices selected, so you can see where they are.
- **Remove Loose Geometry** — sweeps away vertices and edges attached to no face, and faces with no area.

## Notes

- **Only bone vertex groups are touched.** Helper groups are left completely alone, including the Hide Body Under Clothing mask, pin and offset groups for the elastic fit, and anything else you have made. Limiting influences will never eat them.
- Limit Bone Influences is worth running before you export even when nothing complains, since it is the only way to see in Blender exactly what Unity will do.
- Fix Unweighted Vertices needs at least some weighted geometry on the mesh to copy from. If a mesh has no weights at all, it says so and points you at Attach Mesh or Transfer Weights instead.
- The humanoid check uses the toolkit's standard bone names, so run Fix Model first if your rig still uses MMD, Mixamo or VRoid naming.
