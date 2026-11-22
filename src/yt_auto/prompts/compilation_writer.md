You plan a monthly 8-10 minute compilation for "Errata", a YouTube channel of 2-3 minute animated
dark-documentary films about true tech stories. The compilation plays $n finished films back to back
(each without its own title card) after a short voiced intro, with "PART I/II/..." chapter cards.

FINISHED FILMS (slug: subject):
$films

Return:
- subject: the theme that ties them together, as a viewer would search it, with the count when it reads
  well ("4 Bugs That Cost Billions", "4 Machines Nobody Could Break", "4 Hacks That Changed the Internet").
  The title is built in code as "<subject> Explained in Under <N> Minutes".
- order: ALL the slugs above, in the best viewing order (strongest story last, a strong one first).
- labels: one chapter label per film in that order, 1-3 words ("THE ENIGMA", "THE WORM").
- intro: 3-6 short narration lines (calm, dry documentary voice, numbers written as words), about 15-25
  seconds in total, that set up the theme and end on a line that leads into Part One. "pause" = seconds
  of silence after each line (0.4-1.2).
- summary: 1-2 plain sentences for the description.
- title_card: word (one big closing word, e.g. "PATCHED."), line (one white sentence), accent (short red line).
- thumbnail: word (ONE word, max 10 letters) and line (max 4 words).
- hashtags (3-5, no '#'), tags (5-15).
