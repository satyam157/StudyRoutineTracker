import os
import re

def clean_song_name(filename):
    name = filename.replace(".mp3", "")
    name = re.sub(r' \d+ [Kk]bps| Youngistaan', '', name)
    name = name.replace("_", " ").replace("-", " ")
    name = " ".join(name.split()).title()
    icons = {"Perfect": "💍", "Tum Se Hi": "✨", "Phir Bhi": "💖", "Suno Na": "🎵", "Ishq": "🔥", "Rang": "🎨", "Waalian": "🎧"}
    for key, icon in icons.items():
        if key.lower() in name.lower():
            return f"{name} {icon}"
    return f"{name} 🎵"

local_songs = [f for f in os.listdir(".") if f.lower().endswith(".mp3")]
print(f"Total local songs: {len(local_songs)}")
for s in local_songs:
    print(f"File: {s} -> Clean: {clean_song_name(s)}")
