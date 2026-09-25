"""SmartKids EN curriculum catalog (deterministic, 0 TL, no paid inference).

Every episode follows one pedagogical template that the QA gate can verify:
  * exactly 5 scenes, one concept per scene
  * each scene says the target word, asks "Can you say <word>?" and reinforces "<word>!"
  * 45-90 s total, 2-4 s interaction pause after every scene

The factory walks this list in order and never re-uploads an episode that already
has a YouTube video for the same language (idempotency), so the daily run always
picks the next *new* episode. When the list is exhausted the factory pauses with
CONTENT_EXHAUSTED instead of producing duplicates. A Gemini-free-tier topic
generator can later append episodes here / to Supabase episode_dna.

Scene fields:
  key       target word the child repeats (lowercase, used by QA)
  label     big on-screen text
  subtitle  smaller on-screen text
  picture   what is drawn (emoji art / counted objects / geometric shape) — see PICTURES
  bg_hex    background colour (RRGGBB)
  speech    narration (English only)
"""
from typing import Any, Dict, List

TEMPLATE_VERSION = "3.0.0"  # SKQS-1 visual/audio template. Part of the idempotent job_id — bump only when the video template changes.

_COMMON = {
    "age_group": "4-6",
    "format_type": "CONCEPT_EXPLORATION",
    "difficulty": "BEGINNER",
    "target_duration_sec": 55,
    "min_duration_sec": 45,
    "max_duration_sec": 90,
    "characters": [{"name": "Lumi", "type": "Friendly Owl Guide"}],
    "visual_style": "High-contrast flat colour cards with large labels (FFmpeg drawtext)",
    "music_profile": {"profile": "Soft sine chime", "bg_volume_db": -36},
    "safety_profile": {"flash_hazard_guard": True, "zero_violence": True, "no_external_links": True},
}

_EPISODES: List[Dict[str, Any]] = [
    {
        "episode_id": "EP-COLORS-5-V1",
        "family": "colors",
        "title": "Learning 5 Bright Colors with Lumi",
        "learning_objective": "Identify and repeat five colors: red, blue, yellow, green, purple",
        "tags": ["colors", "learn colors", "colors for kids", "preschool learning", "toddlers"],
        "scenes": [
            {"key": "red", "label": "RED", "subtitle": "Sweet Strawberry", "bg_hex": "E53935",
             "speech": "Hello little learners! Today we are going to learn five bright colors. First is red, like a sweet juicy strawberry. Can you say red? Red! Great job!"},
            {"key": "blue", "label": "BLUE", "subtitle": "Ocean and Sky", "bg_hex": "1E88E5",
             "speech": "Now look at the sky and the ocean. Blue! Can you say blue? Blue! Wonderful!"},
            {"key": "yellow", "label": "YELLOW", "subtitle": "Warm Shining Sun", "bg_hex": "FDD835",
             "speech": "Look at the warm shining sun. Yellow! Can you say yellow? Yellow! Fantastic!"},
            {"key": "green", "label": "GREEN", "subtitle": "Green Grass and Frog", "bg_hex": "43A047",
             "speech": "Look at the green grass and the happy frog. Green! Can you say green? Green! Great!"},
            {"key": "purple", "label": "PURPLE", "subtitle": "Purple Grapes and Star", "bg_hex": "8E24AA",
             "speech": "Here is a bunch of purple grapes and a sparkling star. Purple! Can you say purple? Purple! High five! You learned all five colors!"},
        ],
    },
    {
        "episode_id": "EP-NUMBERS-1-5-V1",
        "family": "numbers",
        "title": "Counting 1 to 5 with Lumi",
        "learning_objective": "Count objects from one to five and say each number",
        "tags": ["counting", "numbers for kids", "count to 5", "preschool math", "toddlers"],
        "scenes": [
            {"key": "one", "label": "1", "subtitle": "One ball", "bg_hex": "1E88E5",
             "speech": "Hello friends! Let's count together. Look, here is one little ball. Just one. Can you say one? One! Very good!"},
            {"key": "two", "label": "2", "subtitle": "Two balls", "bg_hex": "43A047",
             "speech": "Now there are more balls. Let's count them. One, two. Two balls! Can you say two? Two! Well done!"},
            {"key": "three", "label": "3", "subtitle": "Three balls", "bg_hex": "FB8C00",
             "speech": "Let's count again, slowly. One, two, three. Three balls! Can you say three? Three! You are so smart!"},
            {"key": "four", "label": "4", "subtitle": "Four balls", "bg_hex": "8E24AA",
             "speech": "Wow, even more balls! Point with your finger. One, two, three, four. Can you say four? Four! Amazing!"},
            {"key": "five", "label": "5", "subtitle": "Five balls", "bg_hex": "E53935",
             "speech": "The last one! One, two, three, four, five. Five balls! Can you say five? Five! Hooray, you counted to five!"},
        ],
    },
    {
        "episode_id": "EP-SHAPES-5-V1",
        "family": "shapes",
        "title": "Five Fun Shapes with Lumi",
        "learning_objective": "Recognize and name five basic shapes",
        "tags": ["shapes", "shapes for kids", "learn shapes", "preschool learning", "toddlers"],
        "scenes": [
            {"key": "circle", "label": "CIRCLE", "subtitle": "Round like a ball", "bg_hex": "1E88E5",
             "speech": "Hello shape explorers! Look at this shape. It is round, like a ball or a cookie. It is a circle. Can you say circle? Circle! Great job!"},
            {"key": "square", "label": "SQUARE", "subtitle": "Four equal sides", "bg_hex": "43A047",
             "speech": "This shape has four sides, and all the sides are the same. It is a square. Can you say square? Square! Wonderful!"},
            {"key": "triangle", "label": "TRIANGLE", "subtitle": "Three sides", "bg_hex": "FB8C00",
             "speech": "Count the sides of this shape. One, two, three. It is a triangle. Can you say triangle? Triangle! Fantastic!"},
            {"key": "star", "label": "STAR", "subtitle": "Shining in the night sky", "bg_hex": "3949AB",
             "speech": "Twinkle, twinkle! This shape shines in the night sky. It has five points. It is a star. Can you say star? Star! Super!"},
            {"key": "heart", "label": "HEART", "subtitle": "A shape full of love", "bg_hex": "D81B60",
             "speech": "The last shape is full of love. It is a heart. Can you say heart? Heart! You learned five shapes. Give yourself a big hug!"},
        ],
    },
    {
        "episode_id": "EP-ANIMALS-5-V1",
        "family": "animals",
        "title": "Farm Animals and Their Sounds with Lumi",
        "learning_objective": "Name five farm animals and the sound each one makes",
        "tags": ["farm animals", "animal sounds", "animals for kids", "preschool learning", "toddlers"],
        "scenes": [
            {"key": "cow", "label": "COW", "subtitle": "The cow says moo", "bg_hex": "6D4C41",
             "speech": "Hello friends! Let's visit the farm. Who is this big animal? It is a cow. The cow says moo, moo. Can you say cow? Cow! Great job!"},
            {"key": "dog", "label": "DOG", "subtitle": "The dog says woof", "bg_hex": "FB8C00",
             "speech": "Here comes a happy animal wagging its tail. It is a dog. The dog says woof, woof. Can you say dog? Dog! Wonderful!"},
            {"key": "duck", "label": "DUCK", "subtitle": "The duck says quack", "bg_hex": "FDD835",
             "speech": "Look who is swimming in the pond. It is a duck. The duck says quack, quack. Can you say duck? Duck! Fantastic!"},
            {"key": "sheep", "label": "SHEEP", "subtitle": "The sheep says baa", "bg_hex": "43A047",
             "speech": "This animal has soft, fluffy wool. It is a sheep. The sheep says baa, baa. Can you say sheep? Sheep! Very good!"},
            {"key": "cat", "label": "CAT", "subtitle": "The cat says meow", "bg_hex": "8E24AA",
             "speech": "And the last animal is small and soft. It is a cat. The cat says meow, meow. Can you say cat? Cat! You met five farm friends!"},
        ],
    },
    {
        "episode_id": "EP-FRUITS-5-V1",
        "family": "fruits",
        "title": "Yummy Fruits with Lumi",
        "learning_objective": "Name five common fruits and their colors",
        "tags": ["fruits", "fruits for kids", "healthy food", "preschool learning", "toddlers"],
        "scenes": [
            {"key": "apple", "label": "APPLE", "subtitle": "Red and crunchy", "bg_hex": "E53935",
             "speech": "Hello friends! Are you hungry? Let's learn some yummy fruits. This fruit is red and crunchy. It is an apple. Can you say apple? Apple! Great job!"},
            {"key": "banana", "label": "BANANA", "subtitle": "Long and yellow", "bg_hex": "FDD835",
             "speech": "This fruit is long and yellow. Monkeys love it! It is a banana. Can you say banana? Banana! Wonderful!"},
            {"key": "orange", "label": "ORANGE", "subtitle": "Round and juicy", "bg_hex": "FB8C00",
             "speech": "This fruit is round and very juicy. Its name is also a color! It is an orange. Can you say orange? Orange! Fantastic!"},
            {"key": "grapes", "label": "GRAPES", "subtitle": "Small and sweet", "bg_hex": "8E24AA",
             "speech": "These little fruits grow together in a bunch. They are grapes. Can you say grapes? Grapes! Very good!"},
            {"key": "watermelon", "label": "WATERMELON", "subtitle": "Green outside, red inside", "bg_hex": "43A047",
             "speech": "This big fruit is green outside and red inside. It is a watermelon. Can you say watermelon? Watermelon! You learned five yummy fruits!"},
        ],
    },
    {
        "episode_id": "EP-COLORS-5B-V1",
        "family": "colors",
        "title": "Five More Colors with Lumi",
        "learning_objective": "Identify and repeat five more colors: orange, pink, brown, black, white",
        "tags": ["colors", "learn colors", "colors for kids", "preschool learning", "toddlers"],
        "scenes": [
            {"key": "orange", "label": "ORANGE", "subtitle": "Like a pumpkin", "bg_hex": "FB8C00",
             "speech": "Hello little learners! Let's learn five more colors today. This color is like a big round pumpkin. Orange! Can you say orange? Orange! Great job!"},
            {"key": "pink", "label": "PINK", "subtitle": "Like a flamingo", "bg_hex": "EC407A",
             "speech": "This color is soft and sweet, like a flamingo standing on one leg. Pink! Can you say pink? Pink! Wonderful!"},
            {"key": "brown", "label": "BROWN", "subtitle": "Like a teddy bear", "bg_hex": "6D4C41",
             "speech": "This color is warm, like a cuddly teddy bear and a tree trunk. Brown! Can you say brown? Brown! Fantastic!"},
            {"key": "black", "label": "BLACK", "subtitle": "Like a magic hat", "bg_hex": "212121",
             "speech": "This color is dark, like the tall hat of a magician. Black! Can you say black? Black! Very good!"},
            {"key": "white", "label": "WHITE", "subtitle": "Like a snowman", "bg_hex": "F5F5F5",
             "speech": "The last color is bright, like a snowman made of fluffy snow. White! Can you say white? White! Hooray, you learned five more colors!"},
        ],
    },
    {
        "episode_id": "EP-NUMBERS-6-10-V1",
        "family": "numbers",
        "title": "Counting 6 to 10 with Lumi",
        "learning_objective": "Count objects from six to ten and say each number",
        "tags": ["counting", "numbers for kids", "count to 10", "preschool math", "kindergarten"],
        "scenes": [
            {"key": "six", "label": "6", "subtitle": "Six stars", "bg_hex": "1E88E5",
             "speech": "Hello friends! You can already count to five. Let's count higher! Here are six stars. Can you say six? Six! Great job!"},
            {"key": "seven", "label": "7", "subtitle": "Seven stars", "bg_hex": "43A047",
             "speech": "One more star makes seven. Six, seven. Seven stars! Can you say seven? Seven! Wonderful!"},
            {"key": "eight", "label": "8", "subtitle": "Eight stars", "bg_hex": "FB8C00",
             "speech": "Another star is here. Six, seven, eight. Eight stars! Can you say eight? Eight! Fantastic!"},
            {"key": "nine", "label": "9", "subtitle": "Nine stars", "bg_hex": "8E24AA",
             "speech": "We are almost there. Six, seven, eight, nine. Nine stars! Can you say nine? Nine! Very good!"},
            {"key": "ten", "label": "10", "subtitle": "Ten stars", "bg_hex": "E53935",
             "speech": "The biggest number today! Six, seven, eight, nine, ten. Ten stars! Can you say ten? Ten! Hooray, you counted to ten!"},
        ],
    },
    {
        "episode_id": "EP-OPPOSITES-5-V1",
        "family": "opposites",
        "title": "Big and Small: Opposites with Lumi",
        "learning_objective": "Understand five pairs of opposites and say the key word",
        "tags": ["opposites", "opposites for kids", "big and small", "preschool learning", "toddlers"],
        "scenes": [
            {"key": "big", "label": "BIG", "subtitle": "Big and small", "bg_hex": "1E88E5",
             "speech": "Hello friends! Today we learn opposites. An elephant is big, and a mouse is small. Big! Can you say big? Big! Great job!"},
            {"key": "up", "label": "UP", "subtitle": "Up and down", "bg_hex": "43A047",
             "speech": "A balloon floats up, up, up into the sky. A ball falls down. Up! Can you say up? Up! Wonderful!"},
            {"key": "hot", "label": "HOT", "subtitle": "Hot and cold", "bg_hex": "E53935",
             "speech": "The sun is hot, and ice cream is cold. Hot! Can you say hot? Hot! Fantastic!"},
            {"key": "fast", "label": "FAST", "subtitle": "Fast and slow", "bg_hex": "FB8C00",
             "speech": "A rabbit runs fast, and a turtle walks slow. Fast! Can you say fast? Fast! Very good!"},
            {"key": "happy", "label": "HAPPY", "subtitle": "Happy and sad", "bg_hex": "8E24AA",
             "speech": "When we play together we feel happy. Happy! Can you say happy? Happy! You learned five opposites. Great work!"},
        ],
    },
]


def _e(*chars, sizes=None):
    return {"emoji": list(chars), **({"sizes": sizes} if sizes else {})}


# One picture per scene (quality rule: no text-only scene). Emoji: Noto Color Emoji, Apache-2.0.
PICTURES = {
    "EP-COLORS-5-V1": [_e("🍓"), _e("🐳"), _e("🌞"), _e("🐸"), _e("🍇")],
    "EP-NUMBERS-1-5-V1": [_e(*["⚽"] * n) for n in range(1, 6)],
    "EP-SHAPES-5-V1": [{"shape": "circle", "color": "FFD54F"}, {"shape": "square", "color": "FFFFFF"},
                       {"shape": "triangle", "color": "FFFFFF"}, {"shape": "star", "color": "FFD54F"},
                       {"shape": "heart", "color": "FFFFFF"}],
    "EP-ANIMALS-5-V1": [_e("🐄"), _e("🐶"), _e("🦆"), _e("🐑"), _e("🐱")],
    "EP-FRUITS-5-V1": [_e("🍎"), _e("🍌"), _e("🍊"), _e("🍇"), _e("🍉")],
    "EP-COLORS-5B-V1": [_e("🎃"), _e("🦩"), _e("🧸"), _e("🎩"), _e("⛄")],
    "EP-NUMBERS-6-10-V1": [_e(*["⭐"] * n) for n in range(6, 11)],
    "EP-OPPOSITES-5-V1": [_e("🐘", "🐭", sizes=[1.0, 0.4]), _e("🎈"), _e("🌞", "🍦"), _e("🐇", "🐢"), _e("😊")],
}
THUMB_TEXT = {
    "EP-COLORS-5-V1": "5 Colors", "EP-NUMBERS-1-5-V1": "Count 1-5", "EP-SHAPES-5-V1": "Shapes",
    "EP-ANIMALS-5-V1": "Farm Animals", "EP-FRUITS-5-V1": "Fruits", "EP-COLORS-5B-V1": "More Colors",
    "EP-NUMBERS-6-10-V1": "Count 6-10", "EP-OPPOSITES-5-V1": "Opposites",
}


def _build(ep: Dict[str, Any]) -> Dict[str, Any]:
    full = dict(_COMMON)
    full.update(ep)
    full["version"] = TEMPLATE_VERSION
    pics = PICTURES[full["episode_id"]]
    for i, sc in enumerate(full["scenes"], start=1):
        sc.setdefault("scene_id", i)
        sc["picture"] = pics[i - 1]
    full["thumb_text"] = THUMB_TEXT[full["episode_id"]]
    return full


CATALOG: List[Dict[str, Any]] = [_build(e) for e in _EPISODES]
CATALOG_BY_ID: Dict[str, Dict[str, Any]] = {e["episode_id"]: e for e in CATALOG}


def get_episode(episode_id: str) -> Dict[str, Any]:
    if episode_id not in CATALOG_BY_ID:
        raise KeyError(f"Unknown episode_id {episode_id}. Known: {list(CATALOG_BY_ID)}")
    return CATALOG_BY_ID[episode_id]


def youtube_metadata(ep: Dict[str, Any], language: str) -> Dict[str, Any]:
    """SEO metadata (EN). Internal IDs are kept out of the public title."""
    words = ", ".join(s["label"].title() if not s["label"].isdigit() else s["key"].title() for s in ep["scenes"])
    description = (
        f"{ep['title']}! In this short interactive video, children aged {ep['age_group']} learn: {words}.\n"
        f"Lumi asks a question after each word and pauses so your child can answer out loud.\n\n"
        f"Learning goal: {ep['learning_objective']}.\n\n"
        "Voice: Piper TTS (LibriTTS-R, CC BY 4.0). Emoji art: Noto Emoji (Apache License 2.0).\n"
        "#SmartKids #KidsLearning #Preschool"
    )
    tags = ["SmartKids", "kids learning", "educational video for kids"] + ep["tags"]
    return {"title": f"{ep['title']} | SmartKids"[:100], "description": description, "tags": tags[:15]}


def episode_dna_row(ep: Dict[str, Any]) -> Dict[str, Any]:
    """Row shape for the Supabase episode_dna table (FK target of pipeline_jobs)."""
    return {
        "episode_id": ep["episode_id"],
        "version": ep["version"],
        "family": ep["family"],
        "title": ep["title"],
        "age_group": ep["age_group"],
        "learning_objective": ep["learning_objective"],
        "format_type": ep["format_type"],
        "difficulty": ep["difficulty"],
        "target_duration_sec": ep["target_duration_sec"],
        "min_duration_sec": ep["min_duration_sec"],
        "max_duration_sec": ep["max_duration_sec"],
        "characters": ep["characters"],
        "visual_style": ep["visual_style"],
        "music_profile": ep["music_profile"],
        "scenes": ep["scenes"],
        "safety_profile": ep["safety_profile"],
    }
