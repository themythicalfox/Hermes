# Hermes Miata — Photorealism Guide

Everything to change after opening the build so renders read as **real
photographs**, not CG. The one-click **Photoreal Polish** button (N-panel →
Hermes) applies all of Part 1 automatically; Parts 2–4 are the manual
finishing touches that scripts can't judge for you, in priority order.

---

## Part 1 — Settings (automated by `photoreal.py`, listed here so you can tweak)

### 1.1 Render properties (Cycles)

| Setting | Stills | Animation | Why |
|---|---|---|---|
| Device | GPU Compute | GPU Compute | — |
| Samples (Max) | **2048** | **512** | paint flake + glass need depth; reel leans on denoiser |
| Adaptive threshold | 0.01 | 0.02 | stop sampling resolved pixels |
| Denoiser | OpenImageDenoise, *Accurate* prefilter, Albedo+Normal | same | best quality CPU/GPU denoise |
| Max bounces | 12 | 12 | — |
| Glossy bounces | **8** | 8 | clearcoat-over-metallic paint is two glossy hits per bounce |
| Transmission | **12** | 12 | windshield + headlight covers + taillight lenses stack |
| Transparent | 16 | 16 | heat-haze planes must never silhouette |
| Clamp Indirect | **10.0** | 10.0 | kills paint-flake fireflies, visually lossless |
| Clamp Direct | 0.0 | 0.0 | never clamp the sun |
| Filter Glossy | 0.5 | 0.5 | softens sparkly caustic noise |
| Caustics | **off** (both) | off | noise for nothing in this scene |
| Pixel filter | Blackman-Harris 1.5 px | same | crisp, photographic edge rendition |
| **Motion blur** | off | **ON, shutter 0.5** | the 180°-shutter rule — biggest single "looks like video" switch |
| Persistent data | ON | ON | huge per-frame speedup |

### 1.2 Output

- **Stills:** 3840×2160, **OpenEXR 32-bit** (grade afterwards; switch to PNG-16 if you want finished files straight out).
- **Animation:** 2560×1440 @ 30 fps, H.264, *Perceptually Lossless*, GOP 15.
- Color Management: **AgX** view transform, look **AgX – Punchy**, exposure **+0.15**, gamma 1.0. AgX's highlight rolloff on sun glints and chrome is the closest thing to film response Blender ships.
- Scene units: Metric, scale 1.0 — **never** scale the car object instead of the camera; DOF blur size is computed from real-world distances.

### 1.3 Camera physics (per camera)

| Camera | Lens | f-stop | Notes |
|---|---|---|---|
| Cam_Orbit | 60 mm | f/4.0 | whole car stays inside DOF |
| Cam_HeroSide | **85 mm** | **f/2.8** | classic compressed hero profile |
| Cam_Rear34 | 50 mm | f/4.0 | |
| Cam_FrontLow | 35 mm | f/5.6 | wide + close needs depth |
| Cam_Interior | 24 mm | f/2.8 | |
| Cam_Shifter | 50 mm | f/1.8 | macro detail, creamy falloff |

All cameras: sensor width **36 mm** (full frame), **9 aperture blades**, slight blade rotation, DOF *focus object* on the car body. Real automotive photography lives between f/2.8 and f/8 — if your background is obliterated to mush at f/1.2, it instantly reads "CG portrait mode".

### 1.4 Per-object fixes

- `shadow_terminator_geometry_offset = 0.1`, `shadow_terminator_offset = 0.05` on every mesh — removes the banded shadow-terminator artefact on the smooth-shaded lofted body, which is one of the most recognisable CG tells.

### 1.5 Compositor (film emulation — all at the edge of perception)

```
Render Layers → Glare(Fog Glow, HIGH, mix −0.92, threshold 1.0)
             → Lens Distortion (Distort 0.004, Dispersion 0.008)
             → ×Vignette (blurred ellipse mask, corners ×0.88)
             → Soft-Light grain (clouds tex, Fac 0.03)
             → Composite
```

Rule of thumb: if you can *name* an effect while looking at the image, halve it.

---

## Part 2 — World / environment (the #1 realism factor, do this first)

1. **Use a real HDRI.** The procedural sky is a fallback; nothing fakes the
   complex reflections a car body needs. Get a free 8k+ `.exr` from Poly
   Haven — best fits for this build:
   - *parking_garage* / *urban_alley_01* (enclosed, moody)
   - *potsdamer_platz*, *industrial_sunset_02* (open lot, golden hour)
   Set it in the N-panel HDRI field **before** building, or swap the
   Environment Texture image in World nodes afterwards.
2. **Rotate the HDRI** (World nodes → Mapping → Z rotation) until the sun
   rakes **across** the body at 30–60° to the camera — side-on light is what
   makes the flake and the flares pop. Never light the car from directly
   behind the camera.
3. **Golden hour beats noon.** If you stay on the procedural sky: sun
   elevation 10–18°, dust density 3+, intensity ~0.55 (Photoreal Polish
   sets this).
4. **Match the ground to the HDRI.** Eyeball the asphalt material's value
   against the HDRI's ground; mismatch in brightness between your plane and
   the horizon line is an instant giveaway. If using a backplate HDRI with
   a visible floor, consider Shadow Catcher on the ground plane instead.
5. Keep the three area fills **subtle** (they exist to draw long "studio
   window" reflections in the paint). If the HDRI is already busy, delete
   `HERMES_FillFront` and halve `HERMES_KeyTop`.

---

## Part 3 — Model finishing touches (open the file and do these by hand)

In rough order of realism-per-minute:

1. **Panel lines.** Real cars are assemblies. Select the body, add edge
   loops tracing hood, doors, and trunk shutlines, bevel them inward
   (~2 mm, profile 1.0) or use a thin boolean strip. Nothing says "toy"
   like a seamless one-piece body.
2. **Decals & plates.** Add a Japanese plate (like the 倉敷 500 in the blue
   reference) as a textured plane, a windshield banner, one or two small
   stickers. Decals break up perfect paint and anchor scale instantly.
3. **Sculpt pass on the loft.** Enter Sculpt Mode on `HERMES_Body` with a
   big Smooth brush and relax any lumpy transitions around the flares and
   nose; then a *very* light Draw pass to crown the hood. 10 minutes here
   is worth 1000 samples.
4. **Stance & life.**
   - Steer the front wheels: rotate both front hub empties ~5–8° around Z.
     Dead-straight wheels look parked by a robot.
   - Add a tiny contact-patch bulge: proportional-edit the bottom tire
     verts outward 3–4 mm where they meet the ground, and drop each tire
     1–2 mm *into* the asphalt so there's no light leak under the contact.
5. **Dirt where physics puts it.** In the paint material, mix a darker,
   rougher variant near the ground using a Geometry → Position Z ramp
   (rocker panels, behind the arches), and dust the rear wheel faces with
   a brownish overlay (brake dust). A 5% effect is enough.
6. **Soft-top wrinkles.** Sculpt 3–4 shallow diagonal tension folds running
   from the B-pillar area toward the rear deck, or add a Cloth sim pinned
   at the rails for one frame and apply it.
7. **Glass details.** Add a barely-visible noise roughness map (0.0→0.08)
   to the windshield for wiper haze; add thin black frit dots around the
   glass border with a gradient texture.
8. **Interior touch-wear.** On the shifter ball, wheel rim at 9 and 3
   o'clock, and the door pull, lighten roughness/darken color slightly
   (vertex-paint a mask into the material) — high-touch sheen sells "used".
9. **Asphalt context.** Scatter a few real-world anchors: a curb stone,
   an oil stain decal under the engine, a drain cover. Empty infinite
   planes scream CG.
10. **Chrome exhaust heat tint** — blue/gold gradient ramp at the tip ends.

---

## Part 4 — Per-shot checklist before pressing F12

- [ ] Camera height between knee and chest (0.4–1.4 m) — drone-height
      "orbit at 2 m" angles look like game captures.
- [ ] Sun/HDRI rotated so a long highlight runs the full body side.
- [ ] DOF focus object set to the nearest headlight/door handle, not the
      car origin.
- [ ] Something out-of-focus in the **foreground** edge of frame (curb,
      another car's mirror) — photographers can't float in empty space.
- [ ] Horizon line not perfectly level for hand-held feel (±0.3° roll on
      stills; keep the reel level).
- [ ] Check an area of pure shadow: it should never be RGB-black. Lift
      with world strength, not lamp energy, if it is.
- [ ] Zoom to 200%: if paint flake sparkles are blinking white pixels,
      raise Clamp Indirect down toward 8, or samples up.
- [ ] For the reel: motion blur ON, and confirm `Persistent Data` is on
      (Render properties → Performance) or frame times will double.

---

### Quick-start order of operations

1. Build (N-panel → *Build Hermes Miata*).
2. Drop in an 8k parking-lot HDRI, rotate to taste.
3. N-panel → **Photoreal Polish** (untick *Animation Profile* for stills).
4. Do Part 3 items 1–4 minimum.
5. Render a 50%-resolution test, fix the Part 4 checklist, then go full res.
