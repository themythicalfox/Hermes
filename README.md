# Hermes — Modded 2002 NB Mazda Miata

**A hyper-realistic, fully procedural Blender 5.1 Python project** that brings a heavily modded Mazda Miata NB (1998–2005) to life with stunning detail.

![Hermes Hero Render](path-to-your-render.png)

### Concept
Hermes is a love letter to the iconic Mazda Miata — reimagined as an aggressive, street-racing inspired roadster. Combining the slammed widebody stance and black soft top from classic modded builds with a custom minimalist luxury interior featuring anodized metal, Alcantara, and retro-futuristic E-ink style displays.

### Features
- **Fully Procedural Modeling**: Every component (body, widebody flares, wheels, interior, exhaust, spoiler) is generated via clean, modular Python scripts.
- **Hyper-Realistic Materials**: Deep metallic British Racing Green paint with clearcoat and orange peel, brushed anodized metal, realistic Alcantara & leather with subsurface scattering, rubber tires with NITTO white lettering, glass, and more.
- **Detailed Interior**: Minimalist racing cockpit with gated shifter, thick Alcantara steering wheel, custom digital displays, Sony-style control panels, and premium textures.
- **Animations**:
  - Subtle exhaust pipe vibration (engine idle)
  - Heat haze/distortion from exhaust tips
  - Soft top open/close
  - Headlights, taillights, and animated blinkers
  - Cinematic orbiting camera rig
- **Scene Setup**: Professional HDR parking lot environment, Cycles rendering, multiple camera angles for both stills and animation.

### Tech Stack
- Blender 5.1 (Python 3.13)
- `bpy` + `bmesh` + Geometry Nodes
- Modular add-on style scripts (`main_miata.py`, `body.py`, `interior.py`, `wheels.py`, etc.)
- Cycles renderer with high-quality PBR materials

### Gallery
*(Add your best renders here — hero shots, interior details, animation GIFs)*

### Project Layout
```
hermes_miata/
├── __init__.py      # add-on registration, sidebar panel & operators
├── main_miata.py    # orchestrator: builds car + scene + animation
├── utils.py         # collections, bmesh primitives, lofting, version-proof
│                    #   Principled BSDF socket helpers, f-curve noise
├── materials.py     # all procedural PBR materials (paint, Alcantara, …)
├── body.py          # lofted widebody shell, wing, diffuser, lights, soft top
├── wheels.py        # bronze multi-spokes, NITTO-lettered tyres, brakes
├── interior.py      # seats, dash, gated shifter, E-ink gauges, Sony panel
├── animation.py     # 300-frame reel: lights, blinkers, top, cameras, jiggle
└── scene_setup.py   # HDRI/sky world, asphalt lot, fill lights, Cycles
run_in_blender.py    # no-install launcher for the Text Editor / headless CLI
```

### How to Use

**Option A — install as an add-on (recommended)**
1. Zip the `hermes_miata/` folder (or `git archive`-export it).
2. Blender → Edit → Preferences → Add-ons → *Install…* → pick the zip → enable **Hermes Miata**.
3. In the 3D Viewport press **N** → **Hermes** tab → **Build Hermes Miata**.
4. (Optional) set an urban parking-lot HDRI path in the panel — e.g. a 4k+
   `.exr` from Poly Haven — otherwise a procedural Nishita sky is used.
5. Use **Render Stills** (six signature angles → `//renders/stills/`) or
   **Render Animation Reel** (300 frames @ 30 fps H.264 → `//renders/`).

**Option B — run without installing**
1. Open `run_in_blender.py` in Blender's Text Editor and press *Run Script*
   (it adds the repo to `sys.path`, hot-reloads the modules, and builds).
2. Or headless: `blender -b -P run_in_blender.py -- --render-stills`
   / `-- --render-reel`.

**Timeline map** (300 frames @ 30 fps): lights sweep on 20–35 · soft top
opens 60–140 · hazard blinkers 80–200 · top closes 200–260 · lights off
270–290 · orbit camera + marker-bound cuts (rear ¾, interior, shifter,
front low, hero side) run the whole reel. Exhaust jiggle, idle vibration
and heat haze are continuous.

**Notes**
- Blinkers use a scripted driver — allow *“Auto Run Python Scripts”*
  (Preferences → Save & Load) or click *Reload Trusted* so they evaluate.
- Tweakables live as custom properties on `HERMES_CarRoot` and as clearly
  named constants at the top of each module (ride height, flare width,
  wing angle, paint flake scale…).
- Re-running the build is idempotent: previous `HERMES_*` objects are
  cleared first.

Built as both a technical showcase of procedural modeling in Blender and a passion project for one of the greatest driver's cars ever made.

---

**"The wingéd messenger"** — swift, agile, and beautifully detailed.

Contributions, feedback, and renders welcome!
