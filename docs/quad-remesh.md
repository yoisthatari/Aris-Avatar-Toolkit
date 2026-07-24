# Quad Remesh (Retopology)

Rebuilds a mesh into clean, evenly flowing quads instead of collapsing triangles the way decimation does.

## What this is

This drives **QuadriFlow**, the field-aligned quad remesher built into Blender. It is the same family of algorithm as commercial retopology tools: it solves for a direction field across the surface and lays quads along it, so edge loops follow the form instead of scattering.

It is not Exoside's Quad Remesher, which is a separate paid plugin and cannot be bundled here. If you own that plugin, it will generally give a nicer result on organic shapes. QuadriFlow is the closest thing that ships with Blender, needs no licence, and for most avatar work it is plenty.

## Decimate or remesh?

| | Decimate | Quad Remesh |
| --- | --- | --- |
| Output | triangles | quads |
| UVs | kept | rebuilt, so they shift |
| Shape keys | kept in Safe mode | **always lost** |
| Best for | shaving a model under a triangle budget | fixing genuinely bad topology |

For simply hitting a VRChat triangle budget, **use Decimate**. Reach for Quad Remesh when the topology itself is the problem: messy sculpts, scan data, or clothing that deforms badly because its edges run the wrong way.

## Usage

1. Select the meshes to retopologise.
2. Pick a target: a **Face Count** (roughly how many quads you want) or a **Ratio** of the current count.
3. Click **Quad Remesh**.

Weights are rebuilt afterwards by transferring them from the original mesh with the same robust inpainting method used for clothing, which gives a better result than raw attribute interpolation. The armature modifier is reconnected for you.

## Options

- **Use Symmetry** — keeps the new topology mirrored. Almost always wanted for avatars.
- **Preserve Boundary** — holds open edges in place, so clothing hems and cuffs stay put.
- **Preserve Sharp** — keeps hard edges crisp rather than rounding them off.
- **Transfer Weights Back** — on by default. Turn it off only if you plan to weight the mesh yourself.
- **Remesh Shape Key Meshes** — off by default, and meshes with shape keys are skipped. Turning it on lets them through, and their shape keys are destroyed.

## Notes

- **Shape keys cannot survive a remesh.** The vertices are all new, so there is nothing for the old deltas to attach to. Remesh before you build visemes and blendshapes, never after. The panel warns you when your selection has shape keys.
- QuadriFlow needs reasonably clean, manifold geometry. If it fails, run Merge Doubles first, and check for loose or interior faces.
- UVs are carried across but are interpolated onto new topology, so expect to touch them up, or unwrap again, before texturing.
- Symmetry assumes the model is centred on X. Apply transforms first if it is not.
