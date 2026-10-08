"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# Words that say nothing about the item. Without this, "looking for a tee"
# scores every listing whose description happens to contain "for" or "a".
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "on",
    "i", "im", "i'm", "me", "my", "want", "need", "looking", "find", "some",
    "something", "anything", "please", "under", "below", "size", "that", "is",
}


def _words(text: str) -> list[str]:
    """Lowercase whole words. 'Tee — 2003 Tour' → ['tee', '2003', 'tour']."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _size_tokens(size: str) -> list[str]:
    """'S/M' → ['s', 'm'],  'XL (oversized)' → ['xl', 'oversized'],  'US 8.5' → ['us', '8.5']."""
    return [t for t in re.split(r"[/\s()]+", size.lower()) if t]


def _size_matches(requested: str, listing_size: str) -> bool:
    """
    A whole-token match, never a substring one — `"s" in "us 9"` is True and
    that's exactly the bug this avoids. One Size listings fit any request.
    """
    tokens = _size_tokens(listing_size)
    if "one" in tokens and "size" in tokens:
        return True
    return requested.strip().lower() in tokens


def _score(keywords: list[str], listing: dict) -> int:
    """+2 per keyword in the title or style tags, +1 if only in description, category or colors."""
    strong = set(_words(listing["title"]) + _words(" ".join(listing["style_tags"])))
    weak = set(
        _words(listing["description"])
        + _words(listing["category"])
        + _words(" ".join(listing["colors"]))
    )
    score = 0
    for word in keywords:
        if word in strong:
            score += 2
        elif word in weak:
            score += 1
    return score


def _price(value: float) -> str:
    """24.0 → '$24', 24.5 → '$24.50'. Matches how a person would write it."""
    return f"${value:.0f}" if float(value).is_integer() else f"${value:.2f}"


def _describe_item(item: dict) -> str:
    """
    The listing as prompt text. Brand is left out entirely when it's None —
    32 of the 40 listings have none, and "Brand: None" ends up in the caption.
    """
    lines = [
        f"Title: {item['title']}",
        f"Category: {item['category']}",
        f"Description: {item['description']}",
        f"Style: {', '.join(item['style_tags'])}",
        f"Colors: {', '.join(item['colors'])}",
        f"Size: {item['size']}",
        f"Condition: {item['condition']}",
        f"Price: {_price(item['price'])}",
        f"Platform: {item['platform']}",
    ]
    if item.get("brand"):
        lines.insert(1, f"Brand: {item['brand']}")
    return "\n".join(lines)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = list(dict.fromkeys(w for w in _words(description) if w not in _STOPWORDS))
    if not keywords:
        return []

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue
        score = _score(keywords, listing)
        if score > 0:
            scored.append((score, listing))

    # sorted() is stable, so ties keep the data file's order.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    items = wardrobe.get("items") or []
    system = (
        "You are a thrift-savvy stylist. Be concrete and brief. Plain text, "
        "no markdown headings."
    )

    if not items:
        prompt = (
            "Someone is thinking about buying this thrifted item. They haven't "
            "saved anything in their wardrobe yet, so do NOT pretend you know "
            "what they own.\n\n"
            f"{_describe_item(new_item)}\n\n"
            "Give general styling advice: two outfit ideas built around this "
            "item, naming the kinds of pieces, colors and shoes that pair with "
            "it. One or two sentences each."
        )
    else:
        closet = "\n".join(
            f"- {w['name']} ({w['category']}; colors: {', '.join(w['colors'])}; "
            f"style: {', '.join(w['style_tags'])}"
            + (f"; note: {w['notes']}" if w.get("notes") else "")
            + ")"
            for w in items
        )
        prompt = (
            "Someone is thinking about buying this thrifted item:\n\n"
            f"{_describe_item(new_item)}\n\n"
            "Here is what they already own:\n"
            f"{closet}\n\n"
            "Suggest one or two outfits that pair the new item with pieces from "
            "that list. Name each wardrobe piece exactly as it's written above, "
            "and don't add pieces they don't own. For each outfit, add one line "
            "on why it works."
        )

    response = generate(prompt, system=system)
    if not response.strip():
        return (
            f"No outfit ideas came back for {new_item['title']} — try again in "
            "a moment."
        )
    return response


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            f"Couldn't write a fit card for {new_item['title']}: there was no "
            "outfit suggestion to build it from."
        )

    system = (
        "You write short, real-sounding social media captions for thrift finds. "
        "Casual and specific, never like a product listing."
    )
    prompt = (
        "Write a caption for a post about this thrift find.\n\n"
        f"{_describe_item(new_item)}\n\n"
        f"How it's being styled:\n{outfit.strip()}\n\n"
        "Rules:\n"
        "- 2 to 4 sentences, plain text, no hashtag block.\n"
        f"- Mention the item, the price written exactly as {_price(new_item['price'])}, "
        f"and the platform written exactly as {new_item['platform']} — once each.\n"
        "- Only mention a brand if one is listed above.\n"
        "- Be specific about the vibe of the outfit, not generic hype.\n"
        "- Don't open with \"Found\" or any line about finding or thrifting it. "
        "Open on a detail of the item or on how it's being worn.\n"
        "- Don't close with \"before I change my mind\", \"keep it for myself\" "
        "or any other line about keeping it."
    )
    response = generate(prompt, system=system)
    if not response.strip():
        return (
            f"Couldn't write a fit card for {new_item['title']}: the model came "
            "back empty — try again in a moment."
        )
    return response
