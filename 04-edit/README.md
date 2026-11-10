# Edit

How Ricky's VSL is put together. Nothing in here needs uploading; it's the editing setup.

## Pieces

- `scripts/transcribe.py`: word-level transcript of the raw video (Whisper large-v3-turbo) → `transcript.json`.
- `scripts/plan.py`: the edit itself. A cue sheet in raw-video time (titles, results cards, phone clips, number
  outlines, top labels, music sections, sound effects) plus pause cutting and caption grouping, compiled into
  `edl.json`.
- `scripts/render.py`: renders the video from `edl.json` and mixes the audio to −14 LUFS.
- `scripts/music.py` / `scripts/sfx.py`: the original score (A minor, 80 BPM, in layers) and sound effects,
  written from scratch, so there's nothing to license.
- `scripts/cards.py`: the results cards made from `02-results-and-b-roll/` (cropped, chargebacks and store name
  hidden, purple outline on the key number).
- `scripts/qa_audio.py` / `scripts/qa_frames.py`: checks: music level under the voice per section, and a still
  from every title, card, outline, clip and label.
- `scripts/voice_chain.txt`: the voice clean-up (low cut, clarity, compression, de-essing).

## Changing something

Edit the cue sheet at the top of `scripts/plan.py` (times are in the raw video, see
`03-raw-vsl-footage/TRANSCRIPT.md`), then run `plan.py` and `render.py` again.

## Version 2 (Iman Gadzhi style)

- `scripts/brand.py`: the look. Near-black plate with a purple glow, per-letter blur-in text, headlines over
  Ricky with a handwritten sub-line (Unbounded + Caveat fonts), framed cards with a glow and slight tilt, photo stickers.
- `scripts/plan2.py`: the v2 cue sheet (title cards, headlines, results on the plate, photos popping up beside
  Ricky, screen recordings in glowing frames, phone clips) → `v2/elements.json`, `v2/text.ass`, `v2/edl2.json`.
- `scripts/compositor.py`: draws the animated graphics frame by frame over the cut footage and burns in the text.
- `scripts/music2.py` + `scripts/music_cues2.py`: the cinematic fallback score (string-style pads, sub swells, low
  pulse) and where each part plays. Swap in licensed tracks when available.

## Version 3

- `scripts/plan3.py`: plain static subtitles (no animation or colour), no animated headlines, screen shares left
  exactly as recorded, results and photos popping up beside Ricky with a thud, title cards kept.
- `scripts/music3.py` + `scripts/music_cues3.py`: the tension score modelled on Iman Gadzhi's bed (breakdown in
  `01-vsls/reference-vsls/IMAN-AUDIO.md`): starts on frame 1, hit after the hook, 115 BPM bass pulse, never silent.
- `scripts/separate.py`, `voice_comb.py`, `gap_music.py`, `analyze_bed.py`: the tools used to study Iman's audio.

## Version 4 audio (real strings)

- `scripts/strings_score.py`: the score played with real recorded strings and percussion from the Versilian Studios
  Chamber Orchestra 2 Community Edition (VSCO 2 CE, public domain / CC0, https://github.com/sgossner/VSCO-2-CE), so it's
  safe for ads. A minor, 115 BPM: cello + bass eighth-note ostinato, viola sixteenth ticks, long swelling violin notes,
  violin tremolo for the hook, timpani rolls into timpani + bass drum + low-string hits.
- `scripts/vsco_index.py`: indexes the samples and checks each one's real pitch.
- Video is the same as version 3; only the music and hits changed (`v3/edl4.json`).

## Version 5 (zooms + strings rewritten after Iman's violins)

- **Zooms on Ricky** (`ZOOMS` in `scripts/plan3.py`, drawn by the `Zoom` class in `scripts/compositor.py`): 13
  moves at the tense lines. Slow push-ins (e.g. the hook into "$87", the mom quote, "everybody was right about me",
  the build into "YouTube Shorts", the guarantee into "60 DAYS") and snap punch-ins ("I was *this close*", "the truth
  is, you don't", "I can't do this anymore", "you're falling for the TikTok scams", "please do not click off").
  Each one cuts back to the wide shot at its end. They're cropped from the 4K original, so they stay sharp, and never
  run during screen shares or title cards.
- **Strings rewritten** (`scripts/strings_score2.py`) after measuring how the strings move in Iman's bed
  (`01-vsls/reference-vsls/IMAN-AUDIO.md`, tool: `scripts/iman_violins.py`): chords every 2 beats over a falling
  A-G-F-E bass, violins re-bowing on every 16th, an E pedal ticking in eighths, a melody that moves with each
  chord, a rising staircase into the reveal and a slide down into "what most people don't understand".
- `scripts/level_score.py`: levels the score per section; the music then sits 2 dB lower than in v4 (`v5/edl5.json`).
- `scripts/render_chunks.sh`: renders the video in parallel chunks that can be resumed.

## Version 6

- **Score rebuilt to match the sound of Iman's bed** (`scripts/strings_score3.py`, compared with
  `scripts/compare_bed.py`): 102 BPM, a ticking tambourine layer in 16ths panned wide, crisp short strings with less
  reverb, a narrower stereo image, a brighter top end and sub under the hits. Findings in
  `01-vsls/reference-vsls/IMAN-AUDIO.md`. The tambourine comes from VSCO 2 CE's "Miscellania Raw" folder (CC0).
- **Music about 1 dB louder than v5** (`v6/edl6.json`).
- **Zooms are smooth now**: every move is a set of keyframes eased in and out (`ZOOMS` in `scripts/plan3.py`), no
  instant punch-ins or snap-backs; where a move starts or ends wide it crossfades with the footage.
- **The opening "$87" is a red number on top of Ricky** (top-left, with "IN SALES." under it) instead of its own black
  page, so you see him lift his phone with the real stats at the same time (`OVERLAY_TITLES` in `scripts/plan3.py`).

## Version 7

- **No booms**: the music has no drums, timpani rolls or sub hits any more (`scripts/strings_score4.py`).
- **More movement in the strings for retention**, after comparing with AB Nasdaq as well as Iman
  (`scripts/music_events.py`): violins alternate every 4 bars between re-bowed pairs (Iman) and broken chords (AB),
  4-bar swells, and a melody that walks into each chord. Sound and level are the same as v6.
- `scripts/level_score.py` now keeps the true section levels (it used to renormalise to the loudest peak, which
  only worked while the booms were the peaks).
- **No zoom on the opening**; the first zoom is "I was this close". The other zooms are unchanged.

## Version 8

- **Music back to v6's violins** (`scripts/strings_score5.py`): v7's alternating broken-chord "tick-tock" violins
  are gone; the strings are exactly v6's, without the booms, playing at v6's level. The light tambourine tick from v6
  sits 2-3 dB quieter.
- **Subtle sound effects** (`scripts/sfx2.py`, built from real CC0 recordings: tambourine, sleigh bells,
  glockenspiel, triangle; cues in `v8/edl8.json`):
  - a cash-register "cha-ching" on the money moments ("$10,000 in just three days" twice, "$300,000",
    "my first $10,000 month", the payout card)
  - three quick, rising lighter ones on "sale after sale after sale"
  - a soft whoosh under the five quicker zooms
  - a soft pop as each number lands on the 01 / 02 / 03 cards and the recap
  - a phone "ding" on "my personal phone number"
  All sit a few dB under Ricky's voice.
- Picture is the same as v7.

## Version 9

- **v6's music exactly**, the version that was liked, with only the long sub "drop" boom under each hit removed
  (`scripts/strings_score3.py --no-sub`). The timpani hits and rolls that build the tension stay. Iman's bed has the
  same shape: short low hits on key phrases about every 15 s and constant string motion, no long crescendos.
  v7/v8 had removed every hit and roll, which flattened the tension.
- Sound effects as in v8 (cash register, pops, whooshes, ding). Picture as in v7.

## Variant A: "Me And The Devil" (instrumental)

- `scripts/song_bed.py` turns the uploaded track into a bed: keeps only its tonal part (harmonic/percussive
  separation drops every kick, 808 hit and snare), cuts everything under 160 Hz so no boom is left (the sub band
  falls from −8 dB to −48 dB relative to the rest), loops it on its own 2-beat grid at the points where the music
  matches best (`variant-a-song/loop_plan.json`), and evens the level so the tension holds the whole 6:19.
- Same picture and sound effects as v9; the music sits about 15 dB under Ricky's voice.
- The song file isn't in this repo (it's copyrighted and this repo is public). Using it in a paid ad needs a licence.

## Variant B: AB Nasdaq style (`scripts/plan_ab.py`, `scripts/cards_ab.py`)

Measured on AB's video first (`scripts/ab_zoom_analysis.py`): a cut every ~4 s between his face, graphics and
proof, and on his face the shot is never still: about 80% of face shots slowly push in or pull out by 15-25% over
5-15 s.

- Word-group captions (2-4 words, one line, white, tight Apple-style sans with a soft shadow, no punctuation).
- Key phrases drop to their own line in heavy electric-blue caps with a glow ("THIS CLOSE", "$10,000 IN 3 DAYS",
  "DO NOT CLICK OFF", "COMPLETELY FREE", "DOWN BELOW"...).
- The always-moving zoom on Ricky, cropped from the 4K original, held wide wherever text needs the empty side.
- The hook as stacked regular + heavy-caps text in the empty left side, then a big blue "$87".
- White keynote cards with black words appearing as he says them; big blue numbers on white ($0, 18,000,000, $87).
- Proof as clean cards on a light-grey keynote plate; photos beside him in thin white frames; clips framed on white.
- "YOUTUBE SHORTS" in giant letters behind his head (his outline cut out per frame with OpenCV GrabCut).
- "The three things" as a list in the empty side of the frame with an arrow on the one he's on.
- The offer as a split screen ("WHAT'S INCLUDED INSIDE YTD") building line by line.
- A whoosh or pop on every graphic, cash-register sounds on the money moments, the boom-free song bed softer
  underneath (17 dB under the voice, like AB's quieter bed).

## Variant B2: AB Nasdaq 1:1 (`scripts/plan_ab2.py`, breakdown in `01-vsls/reference-vsls/AB-BREAKDOWN.md`)

- Word captions exactly like AB's: lowercase, no punctuation, his size and tight spacing, hard switches, now 1-2
  words at a time, over AB's dark fade along the bottom of the frame.
- AB's side text used for ~30 key lines through the whole video: a regular line, then heavy caps with the key word in
  blue, built as Ricky says it (letter-by-letter blur-in) on a white fade from that edge; the bottom captions step
  aside while it's up. The "three things" list sits on AB's dark grey fade instead.
- A subtle mouse click on every caption and every piece of text (no more pops), whooshes on cards, the cash sounds.
- "YOUTUBE SHORTS" now sits fully visible at the top (in front of him, nothing cut off).
- The zoom never moves faster than 5% per second and only drifts while side text needs the room.
- A slot for his diner photo or 2-second clip on "dining server" (both times): upload it to
  `02-results-and-b-roll/` named `diner.jpg` / `diner.mov` (or `.heic`, `.png`, `.mp4`) and it drops in beside him.

## Variant B3 (after review of B2, `scripts/plan_ab3.py`)

- Side text with the white fade only on 13 key moments (it was ~30); the rest are word captions again, plus blue
  emphasis lines ("YOU DON'T", "NOT YOUR FAULT", "THE TIKTOK SCAMS", "RIGHT ABOUT ME", "THAT MONEY"...).
- Word captions back to the smaller size from B (78 px).
- Side text sits a little lower; text and white fade fade out together, opacity only (nothing shrinks or slides in).
- No click sounds on any text. Whooshes on cards, the cash sounds and the phone ding stay.
- No captions while he screen-shares.
- Zooms with intent instead of a constant push/pull: an eased push on the lines that carry weight ("this close",
  "the truth is, you don't", "I can't do this anymore", "the TikTok scams", his mom's line, "don't click off",
  "not what made me that money") and a steady tighter frame in the split screen.
- Fellix: picked up automatically once its font files are installed (it's a paid font, so the files aren't in this
  public repo); until then Inter Display.

## Variant B4 (after review of B3, `scripts/plan_ab4.py`)

- The white side fade only 7 times, softer and narrower (strong only right behind the text), so it breaks the video
  up without taking the focus; the other moments are blue highlight lines at the bottom.
- Full-screen pictures in Iman Gadzhi's premium style instead of white: the dark brand plate, glowing tilted cards with
  the key number outlined, his phone clips in glowing frames.
- More sound on images: a cash register when a money screenshot lands (full screen or beside him), a soft thud on other
  photos and clips, whooshes on everything that comes in. Money said aloud with no picture keeps its cash sound.
- No sound on captions except highlights: a soft whoosh on each blue highlight line, and the money-lost highlights
  ($87, $0, $457, $1,500) in red, landing with a thud.

## Variant B5 (after review of B4, `scripts/plan_ab5.py`)

- The $0 / 18,000,000 / $87 cards in Iman Gadzhi's title-card style: the dark brand plate, big Unbounded numbers
  revealed letter by letter, a spaced sub line and the YTD mark. Money lost in true red, the views in brand purple.
- All the money-lost numbers ($87 in the opening, $0, $457, $1,500, $87) in true red (#FF2222).
- **Colour fix (all renders from now on):** the compositor now converts to and tags HD colour (BT.709). Before, it
  wrote BT.601 without a tag, so browsers showed reds as orange (and every colour slightly off).
- His diner clip (`02-results-and-b-roll/diner.mp4`, 2.2 s) pops up beside him on "dining server" with a soft thud.

## Thank-you video, AB Nasdaq 1:1 (`scripts/ty_*.py`, plan in `thank-you/plan.json`)

Ricky's raw thank-you video (`thank-you-raw-footage` release), edited to the measured breakdown of AB's thank-you video
(`thank-you-vsl-reference/THANK-YOU-BREAKDOWN.md`).

- **Cut:** pauses trimmed only where the audio is truly silent (1 s in total; his delivery is already tight at about 210 words a minute), 2:32.
- **Captions:** AB's: bold white Inter Display (Fellix once the font files arrive), tight tracking, soft drop shadow,
  low on the frame. 1–3 words, each rising in from grey to white as he says it. Off while a full-screen text card is up
  (the card is the caption), on over the application card, the email card and the guru flicker. No sound.
- **Cards** on AB's green gradient (#1F9233 → black), text built word by word in sync with his voice:
  - "That 90% / of other dropshippers couldn't do";
  - "Consistency / Sales", then the Time / Location / Freedom icon circles spinning in;
  - "Countless other dropshippers / in the 1-on-1 Mentorship";
  - "What are the / next steps to joining / the 1-on-1 Mentorship?";
  - a blurred 1-on-1 Mentorship application form popping in;
  - a "Confirm your 1-on-1 call" email popping in;
  - calendar icon + "We only have a / Limited Number of Spots";
  - his doubts as text ("If this is even something / that you can commit to, / or if it can even really work out?");
  - the **red card** "The odds right now are / Stacked Against You" with the falling chart line;
  - a flicker of 12 made-up "online guru" thumbnails (no real people), then "Just trying to push a course / in front
    of your face";
  - shield icon + "To Make You Bulletproof / from the ups and downs of Dropshipping";
  - Ricky shrinking into a window over a scrolling wall of his own Shopify results (chargebacks and store name hidden)
    with "A Profitable / Dropshipper";
  - phone icon + "Be on the lookout / for that call from my team".
- **Light leaks:** 27 warm film-burn flashes (procedural, our own), the cut under the brightest frame, on every card in
  and out and to reset the zoom.
- **Zooms:** opens at 1.5× and eases out; smooth 0.6–1.0 s pushes that stack in two steps to about 1.4× on his key lines,
  reset with a flash or a smooth pull-out; calm stretches stay wide.
- **Music:** original bed to AB's recipe (`scripts/ty_music.py`): G minor, 130 BPM, CC0 upright-piano arpeggio of fifths
  and octaves (VSCO 2 CE) over a soft pad, bells from 0:14, a busier middle, a held high note into "however, on the flip
  side", where a soft 808 on G1 comes in on every downbeat. Flat under the voice (no ducking), 0.5 s fade at the end.
- **No sound effects**, like AB.

## Thank-you video v2 (after review, `scripts/ty_plan2.py`, `ty_render2.py`, `ty_iman.py`, `ty_songbed.py`)

- **Iman Gadzhi-style motion graphics instead of the green gradient**, in the look of the approved B5 cards:
  - the near-black brand plate with the purple arc of light, drifting slowly;
  - wide Unbounded caps that blur in letter by letter as Ricky says each word, with spaced sub lines and
    purple accents;
  - the small YTD mark;
  - icons in glass tiles;
  - the application form, email, guru thumbnails and his results in glowing tilted frames.
- **The red card** ("STACKED AGAINST YOU.") sits on a red version of the plate, with a glowing red chart line falling
  around the text.
- Transitions are the same light flashes, now a clean purple-to-white light sweep in the brand colours.
- **Zooms only with intent:** 8 slow pushes (1.6–2 s, 10–16 %) on his key lines: "one step away", "no reason why",
  "phone in your hand", "locks in your spot", "personally mentoring you" / "exactly why I built", "however, on the
  flip side", "financial freedom". Each one holds until the next card, so it never visibly zooms back out. The calm
  parts stay wide.
- **Music:** the boom-free "Me And The Devil" bed (`song_bed.py`'s de-boomed stem), one unbroken pass ending on the
  song's real outro (no loop joins), about 15 dB under his voice. The song isn't in this public repo (copyright), and
  using it in a paid ad needs a licence.
- Captions, cuts and card timing as in v1.

## FAQ videos (`scripts/faq_plan.py` + the thank-you v2 renderer)

The four raw FAQ videos (`faq-raw-footage` release), edited exactly like thank-you v2 but without music:

- AB's word captions;
- Iman-style cards on the drifting brand plate;
- glass icon tiles;
- purple light sweeps;
- only slow push-ins that hold until the next card;
- cuts on true silence, voice only at −14 LUFS.

| Video | Length | Cards |
| --- | --- | --- |
| How much time (`howmuchtime`) | 0:20 | "2 – 3 HOURS / A DAY. / STILL ABLE TO MAKE DROPSHIPPING WORK.", then "6 PRODUCTS / EVERY SINGLE MONTH." |
| Is it saturated (`issaturated`) | 0:24 | red "HONESTLY DOESN'T WORK ANYMORE." with the falling line; TikTok / Instagram tiles over "INCREDIBLY DIFFICULT TO GET VIEWS AND SALES."; "STRICTLY ON YOUTUBE." |
| Who you work with (`whoworkwith`) | 0:18 | "WITH ME PERSONALLY." with "NOT SOME OTHER ASSISTANT, / NOT SOME OTHER COACH." struck through in red; product / videos / store tiles over "SO YOU DON'T HAVE TO DO ANYTHING YOURSELF." |
| What's inside (`Whatsinside`) | 1:28 | "7 DIFFERENT THINGS.", a numbered card for each of the seven as he names it (01–07), tiles for the coaching-call topics, and a recap of all seven at the end |
