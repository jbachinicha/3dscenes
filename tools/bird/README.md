# Bird

`public/objects/bird/bird.glb` is generated from scratch — modelled, rigged and
animated procedurally in Blender by `bird.py`. There is no source asset.

Style target: the island's other props — faceted low-poly shapes in flat pastel
colours, so the bird is built from coarse icospheres, cones and lofted tubes with
flat shading. It is a sky-blue songbird with a cream belly and a coral beak, to sit
alongside the mint foliage and pink blossom.

## Regenerating

Requires Blender (tested with 5.2 LTS):

```sh
BL=/Applications/Blender.app/Contents/MacOS/Blender
"$BL" --background --factory-startup --python bird.py -- /tmp /tmp/bird.glb

# then compress (260KB -> ~94KB)
npx @gltf-transform/cli optimize /tmp/bird.glb \
  ../../public/objects/bird/bird.glb --simplify false --compress meshopt
```

It prints a diagnostic JSON block and writes preview renders (`bird-flap*.png`,
`bird-perch.png`, `bird-side.png`, `bird-front.png`) to the output directory.

## What it produces

21 bones, 1024 tris, 662 verts, clips `flap` / `glide` / `perch`.

Skinning is **smooth**, not rigid: Blender's heat-diffusion automatic weights leave
502 of 662 vertices influenced by more than one bone. That only works because the
geometry is generated with divisions *spanning every joint* — the wings, neck, tail
and legs are lofted grids and tubes with several rings each. Skin weights are
per-vertex, so a joint in a region with no vertices cannot deform smoothly. (The
chicken had to use rigid weights precisely because its legs had no mid-limb
vertices.)

Bones: `root -> spine1..3 -> {neck1 -> neck2 -> head, tail1 -> tail2,
wing_a -> wing_b -> wing_c (per side), thigh -> shin -> foot (per side)}`.

Detached bits (eyes, beak, feet) are unreliable for heat diffusion, so they are
tagged at build time with `FORCE_<bone>` groups and pinned to a single bone
afterwards.

## Two traps worth knowing about

**Chained bones accumulate.** What you key on a bone is *relative to its parent*,
so a three-segment wing given "-15 degrees" ends up at -45 at the tip. The first
version of this script treated the values as absolute and threw the wings up over
the bird's back. `wingbeat()` now takes per-segment *contributions* (`SEG_AMP`), and
the script asserts the peak tip elevation stays in a believable arc:

    flap 31.4 deg   glide 11.4 deg   perch 15.2 deg

The outward phase lag (`LAG`) is what gives a wingbeat its curl — the tip sweeps
0.78 against the shoulder's 0.30.

**Rotation axes differ per bone.** A bone's local axes depend on its rest
orientation, so the index that produces a given rotation is not the same for every
bone. `axis_for()` resolves it by asking which local axis points along the world
axis being rotated about. Hardcoding an index is how the chicken's legs ended up
swinging sideways.

Leg tuck angles were solved numerically rather than eyeballed, so the toes end up at
the belly line in flight instead of dangling below the body:

    flap -0.50   glide -0.60   perch -0.86   (body bottom -0.40)

## Landing

`index.html` runs each bird through a small state machine:

    cruise --(landTimer)--> descend --> perched --(sit 5-13s)--> takeoff --> cruise

Perch targets are collected as the scene is built (`perchPoints`): the crown of
every tree at `TOP_Y + 1.18*scale`, plus the house roof ridge. Each is flagged
`taken` while claimed so two birds never share one.

Descent and takeoff follow a quadratic bezier. The control point is what gives the
motion its shape — held near cruise altitude for the first two thirds of an approach
so the bird glides in and then drops onto the perch, and lifted above the perch on
takeoff so it climbs out before levelling into the circle. Descent eases out (slows
into the perch), takeoff eases in (heaves off it), and the clip switches to `flap`
over the last 22% of the approach as a flare.

While perched the bird settles upright, lerping its bank and pitch to zero; in
flight it faces its own velocity and banks into the turn.

## Eyes

Eye position is derived from the head ellipsoid — a unit direction scaled by the
head's semi-axes, at 0.88 of the way out — not from hand-picked coordinates. The
first version used eyeballed numbers that put the centres at 0.755 of the head
radius with a radius of 0.23 of it, i.e. entirely *inside* the skull, so the bird
had no visible eyes at all. The script now reports where they landed:

    eye   centre 0.88 of head radius, outermost 1.34
    shine centre 1.12,                outermost 1.30

## Orientation

The bird is modelled facing Blender **-Y**, which the glTF exporter maps to **+Z**,
so `index.html` can use `rotation.y = atan2(vel.x, vel.z)` with no offset.
