# Ari's Avatar Toolkit

Welcome to your lovely new avatar workflow toolkit, handcrafted for Blender 5.2 LTS! 

Inspired by the wonderful but long-unmaintained [Cats Blender Plugin](https://github.com/absolute-quantum/cats-blender-plugin), this add-on has been rebuilt from scratch for the modern Blender Python API and the shiny new Extensions platform. No dusty legacy code, no messy online services, and no bulky bundled importers—just pure, lightweight magic.

Source available: you can peek at the code and use the add-on freely, even for your commercial avatar commissions! (Modification and redistribution are not permitted, though. See our little [LICENSE.md](LICENSE.md)).

---

## Magical Features

### Bringing Models Home (Import & Export)
* **Import Model:** One cute button for every supported format! We handle PMX and PMD through the official MMD Tools extension, VRM through the VRM add-on, and FBX, glTF, OBJ, STL, and Collada through Blender's cozy built-in importers. The imported armature gets selected automatically for you!
* **Install MMD Tools:** One click beautifully installs the official MMD Tools straight from extensions.blender.org (always keeping you up to date without bundling forks!).
* **Export Model:** Flawless FBX export with avatar-safe settings. We preserve your shape keys, sweep away leaf bones, embed textures, ensure Unity-friendly scale, and gently warn you if your model is over 70k triangles.

### Avatar Doctor (Your Pre-Unity Check-Up)
* One click gives your avatar a full health check and groups everything by severity — red will stop your upload, orange will look wrong in game, grey is just good to know. Every issue it can mend comes with its own little fix button right beside it!
* Catches **unweighted vertices** (the classic Unity import blocker), **vertices riding more than 4 bones** (Unity silently drops the extras, so your avatar deforms differently in game than in Blender!), unnormalized weights, missing humanoid bones, unapplied transforms, loose and zero-area geometry, missing UVs, empty material slots, triangle budget, ngons, and bone count.
* **Fix Weights** does the whole weight spa in one click: rescues stranded vertices, trims over-influenced ones, and normalizes everything. It only ever touches bone groups, so your mask, pin, and offset groups stay perfectly safe. See [docs/avatar-doctor.md](docs/avatar-doctor.md).

### The Magic Wand (Fix Model in One Click)
* Translates Japanese bone, shape key, material, and object names. Completely offline using a curated, private dictionary with kana romanization fallback! (No Google Translate, no snooping telemetry.)
* Tidies up and standardizes bone names from MMD, VRoid, Mixamo, Source Engine, and generic FBX rigs into the community-standard scheme (Hips, Spine, Left arm, Eye_L, etc.).
* Rebuilds a clean, gorgeous Hips, Spine, Chest, Neck, and Head hierarchy, and fixes those tricky hips.
* Sweeps away zero-weight junk bones and merges their weights upward.
* Clears out messy MMD rigid bodies, joints, and bone constraints.
* Applies transforms, normalizes your armature modifiers, and neatly joins meshes into a single, perfect `Body` mesh.

### Skeleton & Armature Spa
* **Attach Mesh (Auto Weights):** Parents any mesh to your armature and generates cozy automatic bone-heat weights in a single click.
* **Remove End Bones:** Cleans up leftover end bones (`_end`, `_end_end`, `_End.001`) instantly, blending their weights beautifully into the parents.
* **Merge Weights to Parent:** Works on any selected bones in both edit and pose mode!
* Plus tools to remove zero-weight bones, delete by pattern, and wipe all constraints.

### Pose Boutique
* Start and stop pose mode directly from the panel.
* **Apply as Rest Pose:** A superpower that actually works on meshes with shape keys (which Blender can't do natively!).
* **Store and Restore Pose:** Save your current pose and bring it back later! Perfect for checking weight painting or fixing clipping without losing your spot.
* **Reset Pose:** Snaps the armature straight back to its bind pose without even needing to enter Pose Mode first.

### Wardrobe & Perfect Fits (Clothing & Weights)
* **Elastic Fit:** Gently pushes clothing meshes out of the body with a soft, elastic falloff. It’s UV and topology safe, and brings your shape keys along for the ride! Includes a per-region offset group for extra clearance, and a pin group for vertices that must stay perfectly still.
* **Hide Body Under Clothing:** Sweeps away the body geometry hiding under your outfits, so nothing pokes through and those invisible polygons stop costing you performance. It's a Mask modifier under the hood, so it's completely reversible and your shape keys stay perfectly intact!
* **Robust Weight Transfer:** Flawlessly transfers bone weights from the body to your cute outfits using confident surface matching, plus diffusion inpainting for tricky spots like armpits, chests, and between the legs. No manual smoothing needed! *(An original implementation of the brilliant SIGGRAPH Asia 2023 paper "Robust Skin Weights Transfer via Weight Inpainting".)*

### Attach & Merge (Mix-and-Match Parts)
* **Merge Armatures:** Building your avatar from parts sold separately? When a head or a rigged outfit arrives with its very own armature, this fuses it onto your base in one click. Matching bones join up by name (exact *and* standardized), any extra little bones the part adds (jaws, ears, wiggle bones) are kept and reparented right where they belong, the meshes glide onto your base armature with their weights remapped, and the leftover armature is swept away.
* **Attach Mesh-Only:** Sometimes an outfit is just a bare mesh with no armature at all. Pick your body mesh, select the piece, and this parents it to your base and transfers body weights onto it, with a gentle elastic fit pass first so nothing clips through.

### Substance Painter & Unity
* **Prep for Painter:** One click to get your model paint-ready! Gives every material a clean ASCII name (so Painter's texture sets export with sensible filenames instead of breaking on Japanese characters), drops material slots no face is using, settles the bind pose, and gently warns you about any mesh missing UVs.
* **Export for Painter:** An FBX tuned for texturing — triangulated, tangent space included, metre scale and Y-up, exactly what Painter bakes against and Unity imports cleanly.
* **Import Painted Textures:** Point it at your Painter export folder and it does the rest! Each texture is matched to its material and wired straight into the shader with the right colour space. It even unpacks Unity's packed maps for you: MetallicSmoothness splits into Metallic and (inverted) Roughness, and AlbedoTransparency splits into colour and alpha. Re-import as often as you like — it replaces instead of piling up duplicates.
* **Fix Colour Spaces:** The classic Blender-to-Unity gotcha, solved. Works out from the node links whether each texture is colour or data and tags it sRGB or Non-Colour accordingly, so nothing shows up flat or washed out. See [docs/substance-painter.md](docs/substance-painter.md).

### Gentle Decimation & Retopology
* A global triangle budget distributed proportionally and beautifully across your meshes, with **Safe mode** that promises never to touch meshes that have shape keys.
* **Quad Remesh:** When the topology itself is the problem (messy sculpts, scans, clothing that folds badly), this rebuilds your mesh into clean, flowing quads using Blender's built-in QuadriFlow field-aligned remesher — then transfers your bone weights back onto the new topology with the robust inpainting method and reconnects the armature for you. Symmetry and boundary preservation included! Shape keys can't survive a remesh, so meshes that have them are skipped unless you insist. See [docs/quad-remesh.md](docs/quad-remesh.md).

### Blendshape Kisses (Transfer)
* Copies every shape key from a source mesh to a target mesh, even if they have totally different topologies! Just pick your Source and Target and click **Transfer Blendshapes**.
* **Pre-processing modifiers** make the transfer so much prettier: Subdivision Surface smooths the source for better data, and Displace moves the source geometry along its normals to hug the target. Both have cute viewport toggles!
* **Paintable transfer mask:** Paint red where you want the transfer, and blue where you don't. Includes quick Draw, Reset, and Invert buttons for effortless touch-ups.

### Blendshape Sync
* Magically keeps the exact same shape key active by name across your active object, an Auxiliary object, and every selected mesh! It even pops you into a focused Sculpt Mode session to edit it perfectly. See [docs/blendshape-sync.md](docs/blendshape-sync.md).

### Sweet Visemes
* Generates your 15 standard `vrc.v_*` visemes directly from your basic A, O, and CH mouth shapes, complete with adjustable intensity!

### Bright Eyes (Eye Tracking)
* Sets up your `Eye_L` and `Eye_R` bones for modern, bone-based eye tracking! Handles the renaming, Head parenting, and upright orientation, plus handy buttons to test and reset rotation.

### Shape Key Sculpting
* **Smooth Shape Keys:** Relaxes your shape key deltas to fix crunchy or jagged deformations. Comes with adjustable strength, an optional vertex mask, and safe little backup copies!
* **Apply shape key to basis:** Merges a shape key into your base mesh, keeping a reverted key just in case you change your mind.
* Removes empty shape keys and sweetly sorts your visemes to the very top.
* **Shapekey Batch Creator:** Paste a list of names to instantly generate empty shape keys across all selected meshes! Includes a clickable, paginated list for browsing massive sets. See [docs/shapekey-batch-creator.md](docs/shapekey-batch-creator.md).

### Mesh & Material Makeovers
* Join and separate meshes gracefully, with shape-key-aware merge doubles.
* Merge those pesky duplicate `.001` materials and sweep away unused material slots.
* **Vertex Error Selector:** Paste Unity unweighted-vertex error numbers and it will select *exactly* those vertices in Edit Mode for you! See [docs/vertex-error-selector.md](docs/vertex-error-selector.md).

### Perfect Alignment
* **Vertex/Face Alignment:** Aligns selected objects perfectly to a vertex or face center that you pick on the active object. See [docs/vertex-face-alignment.md](docs/vertex-face-alignment.md).

### The Avatar Analyzer (Beauty Check)
* Scores your avatar against VRChat's official performance ranks (polygons, materials, bones, texture memory) for both PC and Quest! Gives you a lovely little JSON report and highlights heavy meshes and texture hotspots.
* **Creator tools:** Texture Optimizer (power-of-two aware resizing with backups), Mesh Heatmap (to see where your geometry is dense), Auto Fix Avatar (a one-click texture and decimation pass with undo!), Restore Texture backups, and a scene-wide Batch Report. See [docs/avatar-analyzer.md](docs/avatar-analyzer.md).

---

## Cats vs. Ari's Toolkit

| | Cats Blender Plugin | Ari's Avatar Toolkit |
|---|---|---|
| **Blender Support** | 2.79 to 3.6 (abandoned) | 5.2 LTS (Modern & Fresh!) |
| **Packaging** | Legacy add-on (`bl_info`) | Blender Extension (`blender_manifest.toml`) |
| **Translation** | Google Translate (online) | Offline dictionary, private & cozy |
| **Importers** | Bundled forks of mmd_tools | One-click official import, auto-installs MMD Tools |
| **Eye Tracking** | Legacy shape-key based | Modern bone-based |
| **Clothing Tools**| None | Elastic fit & robust weight transfer |
| **Mix-and-Match**| Manual merging | One-click merge armatures & mesh-only attach |
| **Texturing** | None | Substance Painter round trip & colour space fixes |
| **Retopology** | None | QuadriFlow quad remesh with weight transfer |
| **Validation** | Basic | Avatar Doctor with severity levels & one-click fixes |
| **Codebase** | 10 years of patched code | Clean, modular Python magic |

---

## How to Install Your Toolkit

1. Download the latest `ari_avatar_toolkit` zip from our sparkling [Releases](https://github.com/yoisthatari/Ari-s-Avatar-Toolkit/releases) page.
2. In Blender 5.2, open **Edit > Preferences > Get Extensions**. Click the little dropdown arrow in the top right corner, and choose **Install from Disk**. Pick your downloaded zip!
3. Ta-da! The panel will magically appear in your 3D View sidebar (press the `N` key) under **Ari's Toolkit**.

---

## Quick Start Guide

1. Click **Import Model** and pick your file. (If it's a PMX model, just click **Install MMD Tools** first if you haven't yet!)
2. Click **Fix Model**. The toolkit will auto-select your armature if there's only one.
3. Set up your **Visemes** and **Eye Tracking**.
4. Fitting an outfit? Use the Clothing and Weights panel to fit clothing and beautifully transfer your weights.
5. Hit **Decimate** if you're a little over your target platform's polygon budget.
6. Click **Export Model** and bring your gorgeous new FBX right into Unity!

---

## The Library (Docs)

Need a little more help? Step-by-step guides for our special features live happily in the [docs](docs) folder:

- [Blendshape Transfer](docs/blendshape-transfer.md)
- [Vertex/Face Alignment](docs/vertex-face-alignment.md)
- [Avatar Analyzer](docs/avatar-analyzer.md)
- [Blendshape Sync](docs/blendshape-sync.md)
- [Avatar Doctor](docs/avatar-doctor.md)
- [Substance Painter & Unity](docs/substance-painter.md)
- [Quad Remesh (Retopology)](docs/quad-remesh.md)
- [Shapekey Batch Creator](docs/shapekey-batch-creator.md)
- [Vertex Error Selector](docs/vertex-error-selector.md)

---

## Baking from Source

Want to build it yourself? Run this from the repository root:

```bash
blender --command extension build
