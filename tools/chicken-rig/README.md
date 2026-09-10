# Chicken rig

`public/objects/chicken/model.glb` (chicken by jeremy, CC-BY, via Poly Pizza) is a
single rigid mesh with no skeleton, so its legs could never move — all of its
apparent motion came from sliding the whole object around in `index.html`.

These scripts add an armature to that mesh and author its animation clips,
producing `public/objects/chicken/chicken_rigged.glb`.

## Regenerating

Requires Blender (tested with 5.2 LTS):

```sh
BL=/Applications/Blender.app/Contents/MacOS/Blender
"$BL" --background --factory-startup --python animate.py -- \
  . ../../public/objects/chicken/model.glb /tmp/chicken_rigged.glb /tmp

# then compress (drops ~106KB -> ~42KB)
npx @gltf-transform/cli optimize /tmp/chicken_rigged.glb \
  ../../public/objects/chicken/chicken_rigged.glb \
  --simplify false --texture-compress webp --compress meshopt
```

`animate.py` also writes `walk-f*.png` preview renders to the output directory.

## How it works

`riglib.py` finds the joints by measuring the mesh rather than hardcoding guesses:
scanning horizontal spread per height band shows the feet (z 1.3–13, wide), the
thin leg shafts (z 13–48, spread 5–15) and the body (z 48+, spread jumps to 87).
Hence `Z_HIP = 48.5` and `Z_ANKLE = 13.1`; left/right split on the sign of y.

Bones: `root -> hips -> {spine -> head, tail, thigh.L -> foot.L, thigh.R -> foot.R}`.

Weights are rigid (one bone per vertex, weight 1.0). This is deliberate: the mesh
is low-poly with **no vertices mid-limb**, so smooth blending would have nothing
to interpolate between. Rigid segments are also the right look for this art style.

Note the hips are anchored on the leg centroid, not the body centroid — the comb
is dense enough (483 of 1305 verts) to drag the body mean far forward, which would
otherwise place the hips under the head.

### Swing axes (easy to get wrong)

A bone's local axes depend on its rest orientation and roll, so the axis that
swings a limb fore/aft is **not the same index on every bone**. The chicken faces
-X, so a fore/aft stride is a rotation about world **Y**; `swing_axis()` in
`animate.py` finds, per bone, which local axis points along world Y and keys that
one. The resolved axes are `thigh.L/R -> 2`, `foot.L/R -> 0`, `head -> 0`,
`tail -> 0 (inverted)`.

Getting this wrong swings the legs sideways instead of striding, and it is hard to
spot from a 3/4 camera — the two motions look almost identical from that angle.
`animate.py` therefore asserts it numerically, printing the foot's travel per axis;
fore/aft must dominate sideways:

    thigh about local X (wrong):  dX   0.0   dY  21.9
    thigh about local Z (right):  dX -19.7   dY   0.0

`CHICKEN_STRIDE` in `index.html` (0.3746 body heights per cycle) is derived from
the +/-30 degree thigh swing over the 35.4-unit leg, and sets the walk clip's
`timeScale` so the footfalls match the ground speed instead of skating.
