// ════════════════════════════════════════════════════════════════════════════
//  Your gallery — this is the only file you need to edit.
// ════════════════════════════════════════════════════════════════════════════

// Shown on the opening card.
export const TITLE = 'Lantern Way';
export const SUBTITLE = 'Glide through a string of floating photo lanterns.';

// One entry per lantern, in order along the path. Two kinds:
//
//   Single photo lantern
//     caption  the line shown on the lantern's little tag, and in the
//              caption panel that fades in when you glide up close. Keep it
//              short.
//     photo    path relative to public/, e.g. 'lantern-way/01.jpg'. A file
//              that is missing falls back to a generated placeholder, so you
//              can add the photos one at a time.
//
//   Cluster lantern (use `photos` instead of `photo`)
//     caption  same as above.
//     photos   array of 2-4 paths, relative to public/. Shown as a small
//               bundle of prints on one lantern instead of a single pane.
//               Missing files fall back to placeholders individually.
//
// Add or remove entries freely — the path lengthens or shortens to fit, and
// the lanterns re-space themselves.
export const PHOTOS = [
  { caption: 'Where it begins.', photo: 'lantern-way/01.jpg' },
  { caption: 'A good one.', photo: 'lantern-way/02.jpg' },
  { caption: 'Kept this.', photos: ['lantern-way/03.jpg', 'lantern-way/04.jpg', 'lantern-way/05.jpg'] },
  { caption: 'Somewhere golden.', photo: 'lantern-way/06.jpg' },
  { caption: 'Still smiling here.', photo: 'lantern-way/07.jpg' },
  { caption: 'One more for the road.', photo: 'lantern-way/08.jpg' },
];
