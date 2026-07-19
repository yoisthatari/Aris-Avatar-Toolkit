# Shapekey Batch Creator

Create many empty shape keys at once instead of adding them one by one, and browse large shape key lists without scrolling Blender's native list.

## Usage

1. Select the meshes you want the new shape keys added to (or just have one mesh active).
2. In the Shape Keys panel, type a comma-separated list of names into the Batch Creator field, e.g. `Smile, Frown, Angry`.
3. Click Batch Create Shape Keys. An empty shape key is added for each name on every selected mesh (a Basis is added first if the mesh doesn't have one yet). Names that already exist on a mesh are skipped.

## Shape Key List

Click "Shape Key List" to expand a paginated, clickable list of every shape key on the active object, 10 per page. Click a name to jump to it (sets it as the active shape key), and use the `<` / `>` buttons to move between pages.
