# Blendshape Sync

Keep the same blendshape active across multiple objects, and jump straight into a focused Sculpt Mode session to edit it.

## Usage

1. Select the objects you want to keep in sync (or set the Auxiliary field to a specific second object, e.g. teeth or eyelashes, using its eyedropper).
2. Make the object whose shape keys you want to browse the active object. The Shape Key dropdown in the Blendshape Sync panel updates automatically to list that object's shape keys.
3. Pick a shape key from the dropdown.
4. Click Sync Blendshape to turn that shape key on (value 1.0) on the active object, the Auxiliary object, and every other selected mesh that has a shape key with the same name.
5. Click Quick Sculpt Mode to jump into Sculpt Mode on the active object with only that shape key visible, so you can edit it without disturbing the rest of the mesh.
6. Click Reset Synced Shapekeys to clear every shape key value back to 0 on the active object, the Auxiliary object, and every selected mesh, when you are done.
