"""SKQS-2 long-form episodes (8:15 - 10:30) built from topic packs.

Structure (every item follows the same interactive activity loop):
  intro -> for each item: [mystery + 3-2-1 countdown] -> reveal -> repeat-after-me ->
  3 examples -> "Guess!" quiz + 3-2-1 countdown -> answer
  -> dance break (middle) -> review quiz round (countdown each) -> sing-along chant -> outro
If the timeline is shorter than the target, a bonus quiz round is appended automatically.
"""
import random
from typing import Any, Dict, List

TEMPLATE_VERSION = "5.0.0"  # SKQS-3 theatrical long-form template; part of the idempotent job_id

# Acting rule: every narrated line carries an interjection + an emotion tag ([excited] / [whisper] / [calm]).
INTERJECTIONS = ("Wow", "Oh", "Ooh", "Yay", "Oh-oh", "Look", "Hooray", "Woo-hoo", "Whee", "Uh-oh")
PRAISE = ["[excited] Yay! Great job!", "[excited] Woo-hoo! Wonderful!", "[excited] Wow! Fantastic!",
          "[excited] Yay! You're a superstar!", "[excited] Hooray! Well done!", "[excited] Wow, amazing!",
          "[excited] Whee! Super!", "[excited] Yay, you got it! [whisper] So smart!"]
# countdown: clock tick-tock under the spoken "3... 2... 1..."; reveal effects rotate for surprise
COUNT_SFX = [(0.0, "tick"), (0.55, "tock"), (1.1, "tick"), (1.65, "tock"), (2.2, "tick"), (2.75, "go")]
REVEAL_SFX = ["tada", "boing", "chime", "quack", "pop", "tada", "boing", "quack"]
COUNT_WORDS = [(0.05, "[excited] Three!"), (1.15, "[excited] Two!"), (2.25, "[excited] One!")]
DECOR = ["🌸", "🦋", "🐞", "🌼", "🐝", "🌷", "🐛", "🌻", "🍀", "🐌"]


def _ex(e, name):
    return {"e": e, "name": name}


PACKS: List[Dict[str, Any]] = [
    {
        "episode_id": "EP-COLORS-MEGA-V1",
        "family": "colors", "noun": "color",
        "title": "Colors Dance Party! 🍓 Learn Colors for Toddlers & Preschoolers",
        "thumb_text": "Colors Party!",
        "learning_objective": "Recognize and name eight colors using everyday objects",
        "tags": ["learn colors", "colors for toddlers", "colors for kids", "preschool learning",
                 "toddler learning video", "educational videos for toddlers", "kindergarten"],
        "intro": "[excited] Wow! Hello, hello, my little friends! I'm Lumi the owl! [excited] Yay! Today we're going on a super colorful adventure! "
                 "We will find eight beautiful colors, play guessing games, and dance, dance, dance! [whisper] Are you ready? [excited] Let's go!",
        "mystery": "[excited] Ooh! What color is coming next? [whisper] Shh... let's count together!",
        "reveal": "[excited] Wow! It's {K}! [excited] Yay! {K} is {phrase}!",
        "repeat": "[excited] Ooh, say it with me! {K}! [excited] Louder! {K}! [whisper] Wow, you're so good!",
        "example": "[excited] Oh! What else is {k}? Look! {article} {name}! [excited] Yay! The {name} is {k}!",
        "quiz": "[excited] Yay, game time! Oh-oh, which one is {k}? [whisper] Look very, very carefully...",
        "answer": "[excited] Wow! The {name} is {k}! {praise}",
        "review_q": "[excited] Ooh! What color is this? Shout it out!",
        "review_a": "[excited] Yay! It's {k}! {praise}",
        "chant": "[excited] Woo-hoo! Now let's sing all the colors together!",
        "dance": "[excited] Whee! Dance break! Wiggle your arms! Stomp your feet! Clap, clap, clap! [whisper] You're doing so great!",
        "outro": "[excited] Wow, wow, wow! You learned eight colors today: red, blue, yellow, green, purple, orange, pink and brown! "
                 "[whisper] I'm so proud of you. Give yourself a big hug. [excited] Yay! See you next time! Bye bye!",
        "items": [
            {"key": "red", "label": "RED", "bg_hex": "E53935", "pic": "🍓", "phrase": "bright and warm",
             "examples": [_ex("🍎", "apple"), _ex("🚒", "fire truck"), _ex("🍓", "strawberry")]},
            {"key": "blue", "label": "BLUE", "bg_hex": "1E88E5", "pic": "🐳", "phrase": "cool like the ocean",
             "examples": [_ex("🐳", "whale"), _ex("🫐", "blueberry"), _ex("💧", "water drop")]},
            {"key": "yellow", "label": "YELLOW", "bg_hex": "FDD835", "pic": "🌞", "phrase": "sunny and happy",
             "examples": [_ex("🍌", "banana"), _ex("🐤", "baby chick"), _ex("🌞", "sun")]},
            {"key": "green", "label": "GREEN", "bg_hex": "43A047", "pic": "🐸", "phrase": "fresh like the grass",
             "examples": [_ex("🐸", "frog"), _ex("🥦", "broccoli"), _ex("🍀", "clover leaf")]},
            {"key": "purple", "label": "PURPLE", "bg_hex": "8E24AA", "pic": "🍇", "phrase": "royal and magical",
             "examples": [_ex("🍇", "bunch of grapes"), _ex("🍆", "eggplant"), _ex("☂", "umbrella")]},
            {"key": "orange", "label": "ORANGE", "bg_hex": "FB8C00", "pic": "🍊", "phrase": "juicy and bright",
             "examples": [_ex("🥕", "carrot"), _ex("🎃", "pumpkin"), _ex("🍊", "orange")]},
            {"key": "pink", "label": "PINK", "bg_hex": "EC407A", "pic": "🌸", "phrase": "soft and sweet",
             "examples": [_ex("🐷", "piggy"), _ex("🦩", "flamingo"), _ex("🌸", "flower")]},
            {"key": "brown", "label": "BROWN", "bg_hex": "6D4C41", "pic": "🧸", "phrase": "cozy like a teddy bear",
             "examples": [_ex("🧸", "teddy bear"), _ex("🍪", "cookie"), _ex("🐻", "bear")]},
        ],
    },
    {
        "episode_id": "EP-ANIMALS-MEGA-V1",
        "family": "animals", "noun": "animal",
        "title": "Silly Animal Sounds Party! 🐮 Learn Animals for Toddlers & Preschoolers",
        "thumb_text": "Animal Sounds!",
        "learning_objective": "Name eight animals and the sounds they make",
        "tags": ["animal sounds", "learn animals", "farm animals for kids", "toddler learning video",
                 "preschool learning", "educational videos for toddlers", "kindergarten"],
        "intro": "[excited] Wow! Hello, hello, my little friends! I'm Lumi the owl! [excited] Yay! Today we're visiting lots of animal friends! "
                 "We will learn their names, copy their silly sounds, and play guessing games! [whisper] Are you ready? [excited] Let's go!",
        "mystery": "[excited] Ooh! Who is hiding? [whisper] Shh... let's count together!",
        "reveal": "[excited] Wow! It's a {k}! [excited] The {k} {phrase}!",
        "repeat": "[excited] Ooh, say it with me! {K}! [excited] Louder! {K}! [whisper] Wow, you're so good!",
        "example": "{name}",
        "quiz": "[excited] Yay, game time! Oh-oh, which one is the {k}? [whisper] Look very, very carefully...",
        "answer": "[excited] Wow! That's the {k}! {praise}",
        "review_q": "[excited] Ooh! Who is this? Shout it out!",
        "review_a": "[excited] Yay! It's the {k}! {praise}",
        "chant": "[excited] Woo-hoo! Now let's say all our animal friends together!",
        "dance": "[excited] Whee! Dance break! Flap your wings like a duck! Stomp like an elephant! Hop like a bunny! [whisper] You're doing so great!",
        "outro": "[excited] Wow, wow, wow! You met so many animal friends today! [whisper] I'm so proud of you. Give yourself a big hug. [excited] Yay! See you next time! Bye bye!",
        "items": [
            {"key": "cow", "label": "COW", "bg_hex": "6D4C41", "pic": "🐄", "phrase": "says moo, moo",
             "examples": [_ex("🐄", "The cow lives on the farm."), _ex("🥛", "The cow gives us milk."), _ex("🌾", "The cow loves to eat grass.")]},
            {"key": "dog", "label": "DOG", "bg_hex": "FB8C00", "pic": "🐶", "phrase": "says woof, woof",
             "examples": [_ex("🐶", "The dog wags its tail."), _ex("🦴", "The dog loves a bone."), _ex("🎾", "The dog plays with a ball.")]},
            {"key": "cat", "label": "CAT", "bg_hex": "8E24AA", "pic": "🐱", "phrase": "says meow, meow",
             "examples": [_ex("🐱", "The cat is soft and fluffy."), _ex("🧶", "The cat plays with yarn."), _ex("🐟", "The cat likes fish.")]},
            {"key": "duck", "label": "DUCK", "bg_hex": "FDD835", "pic": "🦆", "phrase": "says quack, quack",
             "examples": [_ex("🦆", "The duck swims in the pond."), _ex("💧", "The duck loves water."), _ex("🐤", "The baby duck is so small.")]},
            {"key": "sheep", "label": "SHEEP", "bg_hex": "43A047", "pic": "🐑", "phrase": "says baa, baa",
             "examples": [_ex("🐑", "The sheep has soft wool."), _ex("☁", "The sheep looks like a cloud."), _ex("🌾", "The sheep eats grass.")]},
            {"key": "pig", "label": "PIG", "bg_hex": "EC407A", "pic": "🐷", "phrase": "says oink, oink",
             "examples": [_ex("🐷", "The pig is pink."), _ex("🌰", "The pig loves to eat."), _ex("💦", "The pig plays in the mud.")]},
            {"key": "lion", "label": "LION", "bg_hex": "E53935", "pic": "🦁", "phrase": "says roar",
             "examples": [_ex("🦁", "The lion has a big mane."), _ex("👑", "The lion is the king of the jungle."), _ex("🌞", "The lion sleeps in the sun.")]},
            {"key": "frog", "label": "FROG", "bg_hex": "1E88E5", "pic": "🐸", "phrase": "says ribbit, ribbit",
             "examples": [_ex("🐸", "The frog is green."), _ex("🦗", "The frog catches bugs."), _ex("🍃", "The frog jumps on a leaf.")]},
        ],
    },
]
PACKS_BY_ID = {p["episode_id"]: p for p in PACKS}


def _fmt(tpl: str, item: Dict[str, Any], **kw) -> str:
    k = item["key"]
    return tpl.format(k=k, K=k.capitalize(), phrase=item.get("phrase", ""), **kw)


def _article(name: str) -> str:
    return "An" if name[0].lower() in "aeiou" else "A"


def build_timeline(pack: Dict[str, Any], seed: int = 1, min_total: float = 0.0) -> List[Dict[str, Any]]:
    """Return ordered segments. Durations for narrated segments are filled in after TTS."""
    rng = random.Random(seed)
    items = pack["items"]
    segs: List[Dict[str, Any]] = []
    praise = lambda: rng.choice(PRAISE)  # noqa: E731

    def seg(kind, text=None, fixed=None, sfx=None, chapter=None, **visual):
        segs.append({"kind": kind, "text": text, "fixed": fixed, "sfx": sfx or [], "chapter": chapter,
                     "voice_parts": COUNT_WORDS if kind == "countdown" else [],
                     "visual": dict(kind=kind, **visual)})

    seg("title", pack["intro"], sfx=[(0.0, "chime")], chapter="Hello from Lumi!", title=pack["thumb_text"])
    for idx, it in enumerate(items):
        others = [o for o in items if o is not it]
        seg("mystery", pack["mystery"], sfx=[(0.0, "pop")], chapter=f"{it['label'].title()}", index=idx, total=len(items))
        seg("countdown", None, fixed=3.3, sfx=COUNT_SFX, index=idx, total=len(items), style="mystery")
        seg("reveal", _fmt(pack["reveal"], it), sfx=[(0.0, REVEAL_SFX[idx % len(REVEAL_SFX)])], item=idx)
        seg("repeat", _fmt(pack["repeat"], it), item=idx, pad=2.0)  # kid repeats, music fills
        for ex in it["examples"]:
            text = (_fmt(pack["example"], it, name=ex["name"], article=_article(ex["name"]))
                    if pack["family"] == "colors"
                    else f"[excited] {rng.choice(['Oh!', 'Look!', 'Wow!', 'Ooh!'])} {ex['name']}")
            seg("example", text, sfx=[(0.0, "pop")], item=idx, emoji=ex["e"],
                caption=ex["name"] if pack["family"] == "colors" else it["label"].title())
        correct = rng.choice(it["examples"])
        wrong = [rng.choice(o["examples"]) for o in rng.sample(others, 2)]
        choices = [correct] + wrong
        rng.shuffle(choices)
        ci = choices.index(correct)
        seg("quiz", _fmt(pack["quiz"], it), item=idx, choices=[c["e"] for c in choices])
        seg("countdown", None, fixed=3.3, sfx=COUNT_SFX, item=idx, choices=[c["e"] for c in choices], style="quiz")
        name = correct["name"] if pack["family"] == "colors" else it["key"]
        seg("answer", _fmt(pack["answer"], it, name=name, praise=praise()),
            sfx=[(0.0, REVEAL_SFX[(idx + 3) % len(REVEAL_SFX)])], item=idx,
            choices=[c["e"] for c in choices], correct=ci)
        if idx == len(items) // 2 - 1:
            seg("dance", pack["dance"], sfx=[(0.0, "chime")], chapter="Dance break!", pad=6.0)

    def review_round(label, order):
        first = True
        for idx in order:
            it = items[idx]
            seg("review", pack["review_q"], sfx=[(0.0, "pop")], chapter=label if first else None, item=idx)
            first = False
            seg("countdown", None, fixed=3.3, sfx=COUNT_SFX, item=idx, style="review")
            seg("review_answer", _fmt(pack["review_a"], it, praise=praise()), sfx=[(0.0, "tada")], item=idx)

    order = list(range(len(items)))
    rng.shuffle(order)
    review_round("Guessing game!", order)
    seg("chant_intro", pack["chant"], sfx=[(0.0, "chime")], chapter="Sing-along")
    for rep in range(2):
        for idx, it in enumerate(items):
            seg("chant", f"[excited] {it['key'].capitalize()}!", item=idx, pad=0.9, sfx=[(0.0, "pop")])
    seg("outro", pack["outro"], sfx=[(0.0, "tada")], chapter="Bye bye!", pad=3.0)
    return segs


def bonus_round(pack: Dict[str, Any], seed: int) -> List[Dict[str, Any]]:
    """Extra quiz round inserted before the sing-along when the episode is under the minimum length."""
    rng = random.Random(seed)
    items = pack["items"]
    out = []
    order = list(range(len(items)))
    rng.shuffle(order)
    for n, idx in enumerate(order):
        it = items[idx]
        ex = rng.choice(it["examples"])
        others = [o for o in items if o is not it]
        choices = [ex] + [rng.choice(o["examples"]) for o in rng.sample(others, 2)]
        rng.shuffle(choices)
        name = ex["name"] if pack["family"] == "colors" else it["key"]
        out.append({"kind": "quiz", "text": _fmt(pack["quiz"], it), "fixed": None, "sfx": [(0.0, "pop")],
                    "chapter": "Bonus round!" if n == 0 else None,
                    "visual": {"kind": "quiz", "item": idx, "choices": [c["e"] for c in choices]}})
        out.append({"kind": "countdown", "text": None, "fixed": 3.3, "voice_parts": COUNT_WORDS,
                    "sfx": COUNT_SFX, "chapter": None,
                    "visual": {"kind": "countdown", "item": idx, "choices": [c["e"] for c in choices], "style": "quiz"}})
        out.append({"kind": "answer", "text": _fmt(pack["answer"], it, name=name, praise=rng.choice(PRAISE)),
                    "fixed": None, "sfx": [(0.0, "tada")], "chapter": None,
                    "visual": {"kind": "answer", "item": idx, "choices": [c["e"] for c in choices],
                               "correct": choices.index(ex)}})
    return out


def youtube_metadata(pack: Dict[str, Any], chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
    def ts(sec):
        sec = int(sec)
        return f"{sec // 60}:{sec % 60:02d}"
    words = ", ".join(it["label"].title() for it in pack["items"])
    ch = "\n".join(f"{ts(c['t'])} {c['title']}" for c in chapters)
    description = (
        f"{pack['title']}\n\n"
        f"Join Lumi the owl for about 10 minutes of songs, guessing games and fun! Children learn: {words}.\n"
        "Every part is interactive: guess with the 3-2-1 countdown, repeat the words out loud and dance along.\n\n"
        f"Learning goal: {pack['learning_objective']}.\n"
        "For parents and preschool teachers: pause after each question and let your child answer first.\n\n"
        f"Chapters:\n{ch}\n\n"
        "Voice: Kokoro-82M (Apache License 2.0). Emoji art: Noto Emoji (Apache License 2.0). "
        "Music and sound effects: original, generated by SmartKids.\n"
        "#SmartKids #KidsLearning #Toddlers #Preschool"
    )
    tags = ["SmartKids"] + pack["tags"]
    return {"title": f"{pack['title']} | SmartKids"[:100], "description": description[:4900], "tags": tags[:15]}


def episode_dna_row(pack: Dict[str, Any]) -> Dict[str, Any]:
    """Row for Supabase episode_dna (FK target of pipeline_jobs)."""
    return {
        "episode_id": pack["episode_id"], "version": TEMPLATE_VERSION, "family": pack["family"],
        "title": pack["title"][:255], "age_group": "2-5", "learning_objective": pack["learning_objective"],
        "format_type": "INTERACTIVE_ACTIVITY_LONGFORM", "difficulty": "BEGINNER",
        "target_duration_sec": 560, "min_duration_sec": 495, "max_duration_sec": 630,
        "characters": [{"name": "Lumi", "type": "Friendly Owl Guide"}],
        "visual_style": "Flat colour cards, Noto emoji art, flowers & bugs decorations, animated Lumi",
        "music_profile": {"profile": "procedural cheerful bed", "bpm": 112, "ducking_db": -10},
        "scenes": [{"key": i["key"], "label": i["label"], "examples": [e["name"] for e in i["examples"]]}
                   for i in pack["items"]],
        "safety_profile": {"flash_hazard_guard": True, "zero_violence": True, "made_for_kids": True},
    }
