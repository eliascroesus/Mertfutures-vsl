"""Cut list for Mert's VSL: start on 'I am Mert', trim only true silences between words (ty_plan.plan_cuts)."""
import json, sys
sys.path.insert(0, "/home/user/work/scripts")
from ty_plan import load_words, plan_cuts, mapper, norm
D = "/home/user/work/mert"
RAW_DUR = 263.7067
W = load_words(f"{D}/transcript.json")
i0 = next(i for i in range(len(W) - 2) if [norm(W[i]["w"]), norm(W[i + 1]["w"]), norm(W[i + 2]["w"])][:2] == ["i", "am"]
          and norm(W[i + 2]["w"]).startswith("mert"))
start = round(round((W[i0]["s"] - 0.12) * 30) / 30, 4)
keep = [(max(a, start), b) for a, b in plan_cuts(W[i0:], f"{D}/voice_proc.wav", RAW_DUR) if b > start]
out, dur = mapper(keep)
json.dump({"start_word": i0, "start": start, "keep": keep, "dur": dur}, open(f"{D}/cuts.json", "w"), indent=1)
print(f"starts at {start}s on {W[i0]['w']} {W[i0+1]['w']} {W[i0+2]['w']}; {len(keep)} pieces; {dur:.2f}s "
      f"(raw after start {RAW_DUR - start:.2f}s, trimmed {RAW_DUR - start - dur:.2f}s)")
