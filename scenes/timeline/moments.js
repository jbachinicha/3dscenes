// ════════════════════════════════════════════════════════════════════════════
//  Your timeline — this is the only file you need to edit.
// ════════════════════════════════════════════════════════════════════════════

// Shown on the arch over the road, and on the opening card.
export const TITLE = 'Our Timeline';
export const SUBTITLE = 'Drive down the road and stop at each frame.';

// Engraved on the plate at the heart monument, at the end of the road.
export const ENDING = 'to be continued';

// One entry per checkpoint, in order along the road. Two kinds:
//
//   Single photo frame
//     date     small caps line on the plaque under the frame, and in the
//              caption panel that fades in when you pull up. Keep it short.
//     caption  the sentence in that panel.
//     photo    path relative to public/, e.g. 'timeline/01.jpg'. A file that
//              is missing falls back to a generated placeholder, so you can
//              add the photos one at a time.
//
//   Gallery post (use `photos` instead of `photo`)
//     date, caption  same as above.
//     photos   array of 2-5 paths, relative to public/. Shown as a fanned
//              cluster of prints on one post instead of a single mount.
//              Missing files fall back to placeholders individually.
//
// Add or remove entries freely — the road lengthens or shortens to fit, the
// frames re-space themselves, and the monument moves to the new end.
export const MOMENTS = [
  { date: 'Feb 2026', caption: 'The day it started.', photo: 'timeline/IMG_3026.jpg' },
  { date: 'March 2026', caption: 'Our first date together.', photo: 'timeline/IMG_3275.PNG' },
  { date: 'March 2026', caption: '2nd date ❤️❤️❤️.', photo: 'timeline/IMG_3534.jpg' },
  { date: 'March 2026', caption: 'New activity 🎨.', photo: 'timeline/IMG_3576.jpg' },
  { date: 'March 2026', caption: '1st trip together ❤️', photos: ['timeline/IMG_3741.jpg', 'timeline/IMG_3803.jpg', 'timeline/IMG_4122.jpg', 'timeline/IMG_9386.jpg'] },
  { date: 'April 2026', caption: 'Secretly planning for a gift', photo: 'timeline/IMG_4264.jpg' },
  { date: 'March 2026', caption: 'Lablab nights ❤️', photos: ['timeline/baby.JPG', ] },
  { date: 'March 2026', caption: 'Siquijor 🏝️', photos: ['timeline/IMG_4324.jpg', 'timeline/IMG_4383.jpg', 'timeline/IMG_4691.jpg', 'timeline/IMG_20260502_145916.JPEG'] },

];
