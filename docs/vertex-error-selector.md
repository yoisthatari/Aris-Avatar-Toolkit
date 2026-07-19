# Vertex Error Selector

Turns a Unity unweighted-vertex error into a viewport selection, instead of hunting for the vertices by hand.

## Usage

1. In Unity, copy the vertex index numbers from the error message (e.g. "14149, 14175, 14176").
2. Select the mesh in Blender that the error refers to and make it the active object.
3. Paste the numbers into the Vertex Error Selector panel.
4. Click Select Error Vertices. The tool enters Edit Mode and selects exactly those vertex indices so you can fix the weight paint on them.

## Notes

- Any numbers in the pasted text are used, so you can paste the whole error message, not just the index list.
- Index numbers outside the mesh's vertex range are reported and skipped.
- Vertex indices in a Unity error refer to Unity's post-export mesh, which can differ from Blender's indices after triangulation or UV-seam splitting. This works best right after export, before any further edits to the mesh.
