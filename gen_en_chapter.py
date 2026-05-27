"""Generate Chapter 1 of Chronicle of the Casket in English using DeepSeek API"""
import yaml, os, sys

# Load config
with open(r"H:\Python学习\AI写小说\InkEdge\config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

from openai import OpenAI
client = OpenAI(
    api_key=config["api_key"],
    base_url=config["base_url"],
)

# Load English synopsis
with open(r"H:\Python学习\AI写小说\InkEdge\projects\_import_en\synopsis.txt", "r", encoding="utf-8") as f:
    synopsis = f.read()

# Load Ghost in the City style sample (first chapter)
style_path = r"H:\Python学习\AI写小说\royalroad_archive\Ghost in the City\001_Chapter 1.txt"
with open(style_path, "r", encoding="utf-8") as f:
    style_text = f.read()[:6000]  # First 6K chars for style reference

system_prompt = """You are a professional English cyberpunk novelist. Write in the style of "Ghost in the City" (first-person POV, present tense, punchy paragraphs, internal monologue, gritty urban atmosphere).

IMPORTANT: Write in ENGLISH only. Never use Chinese characters. Use standard English quotation marks.

Your narrative voice: conversational, raw, slightly bitter, self-aware. Short paragraphs. No purple prose. Every sentence earns its place."""

user_prompt = f"""## Project Synopsis
{synopsis}

## Style Reference (Ghost in the City - cyberpunk, first-person, gritty)
{style_text[:4000]}

## Task
Write Chapter 1 of "Chronicle of the Casket" (~3000 words).

Chapter beats:
1. OPEN: Lin Feng, 32, gets fired from his programming job at WeiGuang Tech in near-future Shanghai. Cold HR meeting. He packs his desk. Watches a fresh grad take his old spot.
2. His apartment: mortgage stress, silence, barely-functioning city life. Then the phone call — his grandfather died. The nursing home mentions "the casket" — it's his inheritance.
3. He travels to the ancestral village (bullet train, bus, motorcycle taxi). The decaying house. The locked storage room.
4. He finds the casket. Not wood — a metal alloy he can't identify. No seams. Covered in symbols that look like chemical formulas crossed with circuit diagrams.
5. When he touches the surface, a faint vibration. Then the symbols begin to glow with cold blue light. He hears a voice — not in his ears, inside his head — "Anchor confirmed. Sequence initiating."
6. END: He stares at the glowing casket in the dark storage room, realizing his grandfather didn't leave him a coffin. He left him a door.

Write ONLY the chapter body. No chapter title. Target 3000 words."""

print("Generating Chapter 1...")
response = client.chat.completions.create(
    model=config.get("model_name", "deepseek-v4-flash"),
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    max_tokens=4096,
    temperature=0.8,
)

chapter = response.choices[0].message.content
word_count = len(chapter.split())

# Save
out_dir = r"H:\Python学习\AI写小说\InkEdge\projects\Chronicle of the Casket\chapters"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "chapter_0001.md")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(f"# Chapter 1\n\n")
    f.write(chapter)

print(f"Saved: {out_path} ({word_count} words)")
print(f"Preview:\n{chapter[:300]}...")
