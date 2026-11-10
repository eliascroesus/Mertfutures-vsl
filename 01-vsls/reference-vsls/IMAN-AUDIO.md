# Iman Gadzhi: how his audio builds tension

A closer look at the music and sound in `imangadzhivsl.mp4`, and how Ricky's score copies it.

How it was measured: Iman talks almost nonstop (only 21 pauses long enough to hear the music on its own, about
4 seconds in total), so the music was studied three ways: in those pauses, by filtering out his voice (his speaking
pitch sits around A2, about 110 Hz), and in the deep bass below his voice, where the music is on its own.

## What he does

| What | Measured | Why it works |
| --- | --- | --- |
| Music from the first frame | Bed is already playing under "All right, congratulations…" | No warm-up. You're inside a scene, not watching a video start |
| Thin and airy at first | Almost no bass in the first 3 s (sub-bass around −47 dB) | Leaves room for the hit, and feels unresolved |
| A big hit right after the hook | Sub-bass jumps about 18 dB at 3.3 s and again at 4.4 s, with a whoosh, as the logo slams in | The "oh shit, what is this" moment. Your body reacts before your brain does |
| A driving pulse after the hit | Bass repeats in eighth notes at about 115 BPM, strongest in the first 10 s | Momentum. It feels like something is about to happen |
| It never stops | Speech in 89–99% of every 5 s, music under all of it, loudness range only 2.6 LU | No dead air, so there's never a natural moment to click away |
| Sits under the voice | About 12–15 dB below his voice | Felt more than heard; the words stay clear |
| Hits on graphics | Swooshes on every text card, extra sub hits on key moments (e.g. around 1:35) | Each graphic feels like an event |
| Ends with him | Rings out on an open A–E chord (no third) after the last word | Unresolved and confident at the same time |
| Key | Centres on A | |

## How Ricky's score copies it (`04-edit/scripts/music3.py`, cues in `music_cues3.py`)

- **0:00 to "$87":** starts on frame 1 with an eerie high string cluster (A, B♭, E, a semitone rub) and fast muted
  ticks, no bass, while a riser builds for 5.7 seconds.
- **"$87":** braam-and-boom hit (a cinematic low brass-like stab with a sub drop) with the title card.
- **"I owed money to my mom…":** a driving eighth-note bass pulse at 115 BPM in A, with a low drone.
- **"Then, I changed three simple things":** a second, smaller hit and the chords open up (Am–F–C–G), with the pulse
  following them.
- **The rest:** the pedal pulse and cluster come back for tension (the pain section, the open loop, "don't click
  off", "what most people don't understand"), with a hit on each title card. The only silence is the half second
  before "YouTube Shorts", which lands with the biggest hit. The music sits 12–14 dB under Ricky the whole way and
  rings out on the A drone after "I will see you inside."

## How his strings move (the violin part)

How it was measured: his mix is stereo and his voice sits dead centre, so subtracting the right channel from the
left cancels his voice and leaves only the wide-panned music. That "side" signal is just as loud while he talks as
in his pauses (−43.2 vs −44.1 dB) and barely follows his voice, so it's a clean look at the music. A note-by-note
pitch view of it (`04-edit/scripts/iman_violins.py`) shows this:

| What | Measured | Why it keeps people watching |
| --- | --- | --- |
| Opens on one held note | A held E (E4 + E5) for the first 3 s, nothing else, then the hit | Unresolved; you wait for something to happen |
| The chord changes every ~1.1 s | Every 2 beats, over a bass that walks down A-G-F-E (e.g. 34-37 s, 53-56 s, 74-77 s, 108-111 s) or rocks between A and E | Something moves every second, so the ear never settles and never gets bored |
| Dark "pull" chord | The E chord is E major (G♯) inside A minor, so it pulls back to A and the loop restarts | Feels like it's always about to resolve, never finished |
| Violins don't hold notes, they tick | The same high notes (A5 with E5) re-bowed on every 16th, a new attack every 0.14-0.19 s | Urgency, like a clock running |
| A pedal under it | A repeated E4 in eighths (a new attack every 0.25-0.37 s) | The "ticking" never stops, even when the chords calm down |
| A slow line on top of the chords | Moves one step per chord: C5 → B4 → A4 → G♯4 | A melody you feel without it fighting the words |
| Slide down before a change | 64-68 s: the strings fall from A5 to about C4 over 4 s while he says "only once you are inside the group…", then the music changes at 68.5 s | Tells you "this matters, something new is coming" |
| Accent on the key instruction | A bright chord on "join the WhatsApp group" (61.8 s) | The ask lands as an event |

Pictures: `frames/iman_strings_8-14s.jpg` (ticking 16ths and the E pedal), `frames/iman_strings_73-79s.jpg`
(chords changing every second), `frames/iman_strings_60-80s.jpg` (the slide down at 64-68 s). Time runs left to right,
pitch bottom to top.

**Where Ricky's v4 strings went wrong:** the violins held one note for 4-8 s and the chords changed only every 4-8 s
(every 8 s in the 84-second story section). Nothing moved, which is exactly where you zone out.

**v5 (`04-edit/scripts/strings_score2.py`) copies the movement:**

- A chord every 2 beats in the tense parts (the lament line A-G-F-E) and every bar in the calmer ones.
- Violins re-bowing two chord tones together on every 16th, with violas ticking an E in eighths underneath.
- A melody that steps down one note per chord.
- In the build to "YouTube Shorts", the violins' top note climbs a semitone every bar.
- A 3.5 s slide down into "what most people don't understand".
- The hook opens on a held E like his.

## The sound of his bed vs ours (v6 match)

Measured on the voice-free side signal and in his pauses, then matched one by one (`04-edit/scripts/compare_bed.py`):

| What | Iman | Ours before (v5) | Ours now (v6) |
| --- | --- | --- | --- |
| Tempo | ~101-103 BPM (beat 0.58-0.59 s) | 115 BPM, felt rushed | 102 BPM |
| A ticking layer on top | A shaker/hat tick on every 16th (every 0.145 s), panned wide, crisp (20-23 dB gaps), evenly accented | None | Real tambourine, band-passed to just the jingle tick, a different hit in each ear (every 0.145-0.149 s, 23-25 dB gaps) |
| High strings | Crisp, short, deep gaps between notes (14-18 dB on A5) | Smeared (8-10 dB) | Notes cut to fit their slot, much less reverb on short notes (11-15 dB) |
| Stereo width | Focused: side 15-20 dB under the centre | Very wide and washy (5 dB) | 12 dB |
| Top end (side, vs 315-630 Hz) | 2.5 kHz −21, 5 kHz −12, 10 kHz −23 dB | −25 / −37 / −55 (dull) | −21 / −12 / −24 |
| Deep sub (30-60 Hz) | Felt on the hits | 10 dB too much at first, then matched | Bass drum pitched down under each hit |

The tick is the part you "hear" as tension without noticing it: a clock running under everything. That, the slower
tempo and the crisp, focused strings are the difference between "violins playing" and his "something is about to
happen" feel.

## AB Nasdaq's bed, for comparison (v7)

Same method on `abnasdaqvsl.mp4`: its side signal is music only too (it doesn't follow his voice at all, correlation
−0.02).

- **Held chords underneath, broken chords on top.** A sustained two-note chord in the middle (e.g. C4 + G4) that
  changes every ~2 s. Above it, chords in the 5th octave played as broken, freer rhythms, about 3 attacks a
  second and never on a strict grid (`frames/ab_strings_1-5s.jpg`). It feels played, not programmed.
- **Never stops, and changes texture about as often as Iman's**: a texture change every 9.8 s (median 6 s)
  against Iman's 9.4 s (median 6 s). Neither drops the music out mid-video.
- **No regular pump.** Neither bed has a steady level "pump" (that measured 0.255 s pulse turned out to be my method;
  plain noise gives the same answer).

What both share, and what Ricky's score keeps: something moves at three speeds at once. Fast: Iman's ticks and
re-bowed notes, AB's broken chords. Medium: the chord changes every 1-2 s. Slow: the texture shifts every 6-10 s.

**v7 (`04-edit/scripts/strings_score4.py`):**

- No booms: no drums, timpani, rolls or sub hits.
- The violins switch every 4 bars between Iman-style re-bowed pairs and AB-style broken chords.
- Each 4-bar phrase swells a little and resets.
- The melody walks into the next chord through passing notes.
- The music is never off for more than half a second.

A cleaner breakdown (his music fully separated from his voice) needs the Demucs separation model, whose download
host (`dl.fbaipublicfiles.com`) is blocked in this environment.
