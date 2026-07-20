# Avatar Analyzer

Scores an avatar against VRChat's published performance rank thresholds (Excellent, Good, Medium, Poor, Very Poor) for polygons, materials, skinned and basic mesh counts, bones, and estimated texture memory, then offers one-click cleanup tools.

This only measures what already exists in the Blender file. VRChat-side categories that only exist after uploading to Unity (PhysBones, Contacts, Animators, particle systems, and so on) are not included.

## Usage

1. Open the Avatar Analyzer panel in the sidebar.
2. Pick the Scope (which armature to analyze) and Target platform (PC or Quest).
3. Click Analyze Avatar to see the results, or Export Report JSON to save them to a file.

## Results

- Status: the overall rank (the worst rank across all categories, matching how VRChat itself grades an avatar) and a 0-100 score. The score is our own aggregate for a quick read at a glance, it is not an official VRChat number.
- Per-category rows: current value, rank, and a checkmark or cross against the platform's thresholds.
- Blend Shapes: shown for information only. VRChat does not publish a blend shape limit.
- Fix First: the categories that need the most attention, worst first.
- Heavy Meshes and Texture Hotspots: the biggest contributors, so you know where to spend your optimization time.

## Creator Tools

- Texture Optimizer: resizes every texture used by the avatar down to the Max Texture setting, flooring to the nearest power-of-two size when Force Power-of-Two is enabled. Originals are backed up first.
- Mesh Heatmap: paints a red/blue overlay on the active mesh showing where geometry is densest, as a guide for where to decimate. Click the button again to stop painting.
- Auto Fix Avatar: runs the texture optimizer and, if Auto Add Decimate is enabled, adds non-destructive Decimate modifiers (not applied) to bring heavy meshes toward the platform's Good triangle threshold. Everything happens in one step, so a single Ctrl+Z (or the Undo Auto Fix Session button) undoes it all.
- Restore Texture Size Backup: brings every texture resized by the Texture Optimizer or Auto Fix Avatar back to its original size and pixel data. Texture resizing is not reliably covered by Blender's normal undo, so use this instead of Ctrl+Z to walk back a texture resize.
- Batch Report (Scene): analyzes every armature in the scene at once, useful when you have more than one avatar in the file.
