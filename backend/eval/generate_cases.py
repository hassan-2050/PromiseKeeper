"""Create a labeled, synthetic 55-case smoke corpus. Not a measured benchmark."""
import json
from pathlib import Path

patterns = [
 ("explicit", "Maya: I'll send the revised report by Friday.", "send the revised report", "Maya", "Friday"),
 ("implicit", "Jon: The cleaned figures will be in your inbox tomorrow.", "share the cleaned figures", "Jon", "tomorrow"),
 ("vague", "Lee: I'll get to that soon.", "get to that", "Lee", None),
 ("conditional", "Sam: If the review passes, I'll upload the appendix.", "upload the appendix", "Sam", None),
 ("fulfilled", "Nia: I sent the consent forms this morning.", None, None, None),
 ("negated", "Omar: I won't be able to send the draft.", None, None, None),
 ("hypothetical", "Rae: I could send the slides if you need them.", None, None, None),
 ("multi-speaker", "Pia: Can you check the table?\nDev: Yes, I'll check the table today.", "check the table", "Dev", "today"),
 ("ambiguous", "Kai: Someone should circle back on the results.", "circle back on the results", None, None),
 ("duplicate", "Mira: I'll send the report tomorrow.\nMira: I'll send the report tomorrow.", "send the report", "Mira", "tomorrow"),
 ("explicit-date", "Rae: I will send the consent summary on 2026-11-03.", "send the consent summary", "Rae", "2026-11-03"),
]
rows=[]
for i in range(len(patterns) * 5):
 category,text,claim,owner,deadline=patterns[i%len(patterns)]
 round_index = i // len(patterns)
 speaker_names = ["Ari", "Nora", "Eli", "Bea", "Sol"]
 if owner:
  original_owner = owner
  owner = speaker_names[(round_index + i) % len(speaker_names)]
  text = text.replace(original_owner, owner)
  # In the multi-speaker example, vary the other participant too.
  if category == "multi-speaker":
   text = text.replace("Pia", speaker_names[(round_index + i + 2) % len(speaker_names)])
 elif category in {"fulfilled", "negated", "hypothetical", "ambiguous"}:
  first = text.split(":", 1)[0]
  text = text.replace(first, speaker_names[(round_index + i) % len(speaker_names)], 1)
 # Give each short exchange distinct surrounding context without changing the
 # labeled obligation itself. Every row remains authored and synthetic.
 if i >= len(patterns):
  text = f"Weekly lab sync · discussion {i + 1}\n{text}"
 # Relative wording cannot be anchored without a source timestamp, so the
 # expected normalized deadline is unresolved (null).
 gold_deadline = deadline
 if deadline and deadline.casefold() in {"today", "tomorrow", "friday"}:
  gold_deadline = None
 rows.append({"id":f"synthetic-{i+1:02d}","category":category,"text":text,"gold":{"commitment":claim is not None,"claim":claim,"owner":owner,"deadline":gold_deadline},"synthetic":True})
Path(__file__).with_name("cases.jsonl").write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows),encoding="utf-8")
