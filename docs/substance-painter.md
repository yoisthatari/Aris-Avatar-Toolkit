# Substance Painter & Unity

A round trip between Blender, Substance Painter and Unity, with the fiddly parts handled for you: texture set naming, tangents, and colour spaces.

## Sending the model to Painter

1. Select the meshes you want to paint, or leave nothing selected to use the whole model.
2. Click **Prep for Painter**. This:
   - renames every material to a clean ASCII name (Japanese names are run through the offline dictionary first), because Substance Painter names each texture set after its material and non-ASCII names break the exported filenames
   - removes material slots that no faces actually use, so you do not get empty texture sets
   - settles the armature back into its bind pose
   - warns about any mesh with no UV map, since those cannot be painted
3. Click **Export for Painter** and pick a location.

The FBX is written with triangles, tangent space, metre scale and Y-up, which is what Painter expects for baking and what Unity expects on import.

## Bringing the textures back

1. In Substance Painter, export your textures. Both the default naming and the Unity presets are understood.
2. Click **Import Painted Textures** and pick the folder you exported to.

Each file is matched to its material by the texture set name and wired into the Principled BSDF:

| Painter / Unity map | Where it lands |
| --- | --- |
| BaseColor, Albedo, Diffuse | Base Color |
| AlbedoTransparency, BaseColorOpacity | Base Color + Alpha |
| Normal, NormalGL | Normal Map node |
| Metallic | Metallic |
| Roughness | Roughness |
| Smoothness, Glossiness | inverted into Roughness |
| MetallicSmoothness | Red into Metallic, Alpha inverted into Roughness |
| Emissive, Emission | Emission Color, strength 1 |
| AO, Height | loaded and placed, left unconnected |

Colour spaces are set as it goes: colour maps stay sRGB, data maps become Non-Colour.

## Fix Colour Spaces

The classic Blender-to-Unity gotcha. If a normal or metallic map is tagged sRGB, shading goes flat or washed out. **Fix Colour Spaces** walks every texture, works out from the node links whether it feeds a colour or a data socket, and corrects it.

Useful on models you imported from elsewhere, not just ones you painted.

## Notes

- Re-importing is safe. Nodes the toolkit created are tagged and replaced, so you can paint, re-export and re-import without piling up duplicates.
- AO and Height are loaded but left unconnected on purpose; they are usually destined for Unity's occlusion slot rather than the Blender preview.
- If Painter exported DirectX normals, the import warns you. Blender and Unity both want OpenGL, so re-export with the OpenGL preset rather than flipping the green channel by hand.
- Nothing here touches your UVs or topology.
