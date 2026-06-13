# Modeling the NB Miata Yourself — Step-by-Step Guide

You're right that hand-modeling will beat the procedural build for looks —
scripts can place geometry, but car bodies live or die on *surface flow*,
and that's a human eye skill. This is the professional subdivision-surface
car workflow, adapted to the NB and this project's scene (the procedural
materials, animation, cameras and scene all still work with a hand-built
body — see "Plugging into Hermes" at the end).

Budget: a first car body takes most people 10–20 hours. It's the single
best modeling exercise there is.

---

## Stage 0 — Reference setup (30 min, do not skip)

1. Get NB Miata **blueprints** (front/side/top/rear orthographic line
   drawings — search "Mazda MX-5 NB blueprint"; the-blueprints.com has
   them) plus 20–30 photos: your green/blue reference cars, plus factory
   press shots at 3/4 angles.
2. In Blender: `Add > Image > Reference` for each blueprint view. Place:
   side view on the X-plane, front view on the Y-plane, top view on the
   ground. **Scale them to real size first** — the NB is 3.945 m long,
   1.68 m wide (stock; your widebody adds ~100 mm per side), 1.23 m tall
   (yours sits lower). Use a 3.945 m reference cube to match them.
3. Set units: Scene Properties → Metric, Unit Scale 1.0. Real-world scale
   is non-negotiable — DOF, shadows, and HDRI lighting all assume it.
4. Put references in their own collection, enable "Show in front" OFF,
   set opacity ~0.4.

## Stage 1 — Block-out (1 hour)

Goal: a 200-polygon "soap bar" that nails the proportions. Resist detail.

1. Add a cube, scale to the car's bounding box, then in Edit Mode add
   loops at: nose, front axle, cowl (windscreen base), seat line, rear
   axle, tail. Shape *only* the side profile silhouette first against the
   side blueprint — the NB's identity is in that silhouette: low rounded
   nose, hood rising to the cowl, fast windscreen, high rounded tail.
2. Then shape the top view: plan taper — widest at the doors, pulling in
   smoothly to nose and tail.
3. Then the front view: tumblehome (body leans inward above the
   beltline), widest point at mid-door-height ("hips").
4. Mirror modifier across X from the very start. Only ever model half.
5. Sanity check from a 3/4 view against photos at eye level — *not* from
   above (everything looks fine from above).

## Stage 2 — The subsurf cage (the main event, 4–8 hours)

1. Add a Subdivision Surface modifier (level 2) to your block-out. From
   now on you edit the low-poly **cage** and judge the smooth result.
2. Keep the cage COARSE — this is the #1 beginner mistake. A whole NB
   body cage needs only ~600–1200 faces. More verts = lumps. If a surface
   looks lumpy, *remove* edge loops, don't add them.
3. **Edge flow rules for cars:**
   - Loops should run the directions water would flow off the car: along
     the length of the body, and around the wheel arches in concentric
     rings.
   - The wheel-arch openings need 8–12 edge "spokes" radiating from them;
     start them by inset-ing a circular region around each arch.
   - One continuous loop must trace the beltline nose-to-tail.
   - Where the fender meets the hood, keep loops parallel to the seam —
     you'll cut along it later.
4. **Character lines:** the NB has soft ones. Create them with *holding
   edges* (a second loop close to the line edge) or edge creasing
   (Shift+E, ~0.6) — never with sharp single edges.
5. Check surfacing constantly with a glossy **Matcap** (viewport shading
   sphere icon → reflective matcap) or a checker HDRI: drag the view and
   watch the reflections sweep. Smooth unbroken reflection bands = good
   surface. Wobbling bands = move cage verts a millimetre at a time until
   they stop. This "reflection reading" is 50% of the whole skill.
6. Model the arches as if stock first, then select the arch rings and
   fatten them outward (Alt+S shrink/fatten with proportional editing)
   for the widebody flare — that keeps them symmetrical and smooth.

## Stage 3 — Splitting into panels (1–2 hours)

This is exactly what you asked for, and the pro order is what the script
now mimics: **model the body as ONE continuous mesh, split panels after.**
Panels cut from one surface always line up; panels modeled separately
never do.

1. Mark the shutlines: select the edge loops along hood/fender seams,
   door gaps, trunk seam, bumper seams. (If a seam has no loop, add one
   with the Knife tool ([K]) snapped along the panel line.)
2. With a seam loop selected: Edge menu → **Edge Split**, then in face
   select mode hover over a panel and press [L] (select linked), then
   [P] → *Selection* to separate it into its own object. Repeat for:
   front bumper, hood, each front fender, each door, each rear quarter,
   trunk lid, rear bumper. The leftover (cowl, tub, tail panel) stays as
   the "shell".
3. Give every panel a **Solidify** modifier (1.5 mm, even thickness) —
   real sheet metal — and a small Bevel (0.5–1 mm, 2 segments) so panel
   edges catch highlights.
4. Open the gaps: on each panel, select its boundary loop (Select →
   All by Trait → Non Manifold), then shrink it inward 1.5–2 mm
   (Shift+Alt+S to shrink along normals, or just scale slightly toward
   the panel's median). Real shutlines are 3–4 mm total.
5. Set each panel's origin to its own centre (Object → Set Origin →
   Origin to Geometry) so doors/hood can later be hinged.

## Stage 4 — Details that sell it (2–4 hours)

In descending value-per-minute:
- **Window recess:** glass sits ~6 mm *inside* the body surface with a
  rubber-seal channel — duplicate the opening edge, inset, drop in.
- **Headlight/taillight buckets:** model the recess into the body, lamp
  inside it, clear cover flush with the body surface.
- Door handles, fuel filler door (circle inset on the right quarter),
  badges, wiper arms, antenna.
- Arch liners: simple black half-tube inside each wheel well so you never
  see through to the far side.
- Exhaust tips visible through a cut in the rear valance, not floating.
- Use the procedural `hermes_miata` wing/diffuser/wheels as-is or as
  blockouts to replace — they're independent objects.

## Stage 5 — Interior & drivetrain

The packaging numbers that the script now uses (and that you should keep,
since they're real-car correct):
- Windscreen base y≈0.51 m ahead of mid-wheelbase; dash face right behind
  it; steering wheel centre ~0.45 m behind the dash face, 0.58 m high.
- Seats: backrest ~0.5 m ahead of the rear axle — leaving the fuel-tank
  bay (≈0.7 × 0.35 × 0.17 m) between seat backs and axle.
- Engine: behind the front axle (front-mid), gearbox under the tunnel,
  driveshaft to a diff at the rear axle.
Model the dash as one swept profile (curve + bevel or a box with loops),
and steal the procedural gauge/switch/shifter parts — small greebles are
where procedural actually wins.

## Stage 6 — Common failure modes (check against your screenshot)

| Symptom | Cause | Fix |
|---|---|---|
| Blobby "rock" body | cage too dense / verts off-surface | delete loops, read reflections (Stage 2.5) |
| Floating parts | object origins at world origin, rotation applied to object | set origin to geometry before rotating |
| Wireframe boxes everywhere | live boolean cutters on display-wire | apply booleans, delete cutters |
| Interior invisible | parts placed outside the cabin volume | block a human silhouette (1.75 m) in the seat and build around it |
| Toy-like scale feel | wrong real-world size | 3.945 m nose-to-tail, verify with the measure tool |

---

## Plugging into Hermes

The scripted scene is modular — your hand-built body drops straight in:
1. Build/keep the scene: `Build Hermes Miata`, then delete the generated
   panels in `Hermes_Miata_Body` you intend to replace.
2. Name your panels anything, parent them to `HERMES_BodyPivot` (so they
   inherit the idle vibration), and assign the existing
   `HERMES_CarPaint_BRG` material — flake, orange peel and clearcoat come
   for free.
3. Wheels, interior, drivetrain, lights, cameras, animation and the
   photoreal pass all keep working untouched.
