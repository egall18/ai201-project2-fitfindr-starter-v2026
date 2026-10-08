"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import suggest_outfit, create_fit_card
from generate import ModelUnavailable
from mcp_client import MCPError, call_tool


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── query parsing ─────────────────────────────────────────────────────────────

# "under $30", "below 30", "less than $30", "max $30", "up to $30", or a bare "$30".
_PRICE = re.compile(
    r"(?:\b(?:under|below|less than|max(?:imum)?|up to)\s*\$?|\$)\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
# "size M", "size 8.5", "size W30", "size S/M".
_SIZE = re.compile(r"\bsize\s+([a-z0-9./]+)", re.IGNORECASE)
_EDGE_FILLER = {
    "i'm", "im", "i", "looking", "for", "a", "an", "some", "want", "need",
    "in", "max", "and", "with",
}


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max_price out of plain language, by regex.

    'vintage graphic tee under $30, size M'
        → {'description': 'vintage graphic tee', 'size': 'M', 'max_price': 30.0}

    Whatever isn't a price or a size becomes the description, with filler
    trimmed off the ends. Filler in the middle stays — search_listings ignores it.
    """
    max_price = None
    price_match = _PRICE.search(query)
    if price_match:
        max_price = float(price_match.group(1))

    size = None
    size_match = _SIZE.search(query)
    if size_match:
        size = size_match.group(1).upper()

    description = query
    for match in (price_match, size_match):
        if match:
            description = description.replace(match.group(0), " ")
    description = re.sub(r"[,$]", " ", description)
    description = re.sub(r"\s+", " ", description).strip()
    # Trim filler left at the edges ("looking for a …", "… in") so the
    # no-results message quotes what the user actually asked for.
    words = description.split()
    while words and words[0].lower() in _EDGE_FILLER:
        words.pop(0)
    while words and words[-1].lower() in _EDGE_FILLER:
        words.pop()
    description = " ".join(words)

    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """Say what the user could change, based on which filters they actually used."""
    if not parsed["description"]:
        return (
            "I couldn't tell what you're looking for. Add a few words about the "
            "item, like 'denim jacket' or 'graphic tee'."
        )

    asked = f"'{parsed['description']}'"
    if parsed["size"]:
        asked += f" in size {parsed['size']}"
    if parsed["max_price"] is not None:
        asked += f" under ${parsed['max_price']:g}"

    changes = []
    if parsed["max_price"] is not None:
        changes.append(f"raise your budget above ${parsed['max_price']:g}")
    if parsed["size"]:
        changes.append(f"drop the size {parsed['size']} filter")
    changes.append("use broader keywords (e.g. 'dress' instead of a specific style)")

    return (
        f"Nothing matched {asked}. Try to "
        + ", ".join(changes[:-1])
        + (", or " if len(changes) > 1 else "")
        + changes[-1]
        + "."
    )


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    trace.start_trace()
    session = new_session(query, wardrobe)
    session["parsed"] = parse_query(query)
    trace.step("parse_query (regex)", inputs=query, returned=str(session["parsed"]))

    # Each pass runs one step and decides the next one from what that step put
    # in the session. None means the run is over, finished or stopped.
    next_step = "search"
    iterations = 0

    while next_step is not None:
        iterations += 1
        trace.check_iterations(iterations)

        if next_step == "search":
            parsed = session["parsed"]
            arguments = {
                "description": parsed["description"],
                "size": parsed["size"],
                "max_price": parsed["max_price"],
            }
            # search_listings runs on the MCP server (mcp_server.py), not in-process.
            try:
                session["search_results"] = call_tool("search_listings", arguments)
            except MCPError as exc:
                session["error"] = (
                    "The listing search couldn't be reached, so nothing was "
                    f"searched. Try again in a moment.\n  ({exc})"
                )
                trace.step("search_listings (via MCP)", inputs=str(arguments),
                           note="MCP call failed, stopping")
                next_step = None
                continue

            # THE BRANCH: nothing found means stop here, before any model call.
            if not session["search_results"]:
                session["error"] = _no_results_message(parsed)
                next_step = None
                note = "branch: empty, stopping before suggest_outfit"
            else:
                session["selected_item"] = session["search_results"][0]
                next_step = "suggest"
                note = "branch: results, selected_item = search_results[0]"
            trace.step("search_listings (via MCP)", inputs=str(arguments),
                       returned=session["search_results"], note=note)

        elif next_step == "suggest":
            owned = len(session["wardrobe"].get("items", []))
            try:
                session["outfit_suggestion"] = suggest_outfit(
                    session["selected_item"], session["wardrobe"]
                )
            except ModelUnavailable as exc:
                _stop_model_unavailable(session, "suggest_outfit", exc)
                next_step = None
                continue
            trace.step(
                "suggest_outfit",
                inputs=session["selected_item"],
                returned=session["outfit_suggestion"],
                note=f"wardrobe: {owned} items" if owned
                else "wardrobe: empty, general styling advice",
            )
            next_step = "fit_card"

        elif next_step == "fit_card":
            try:
                session["fit_card"] = create_fit_card(
                    session["outfit_suggestion"], session["selected_item"]
                )
            except ModelUnavailable as exc:
                _stop_model_unavailable(session, "create_fit_card", exc)
                next_step = None
                continue
            trace.step("create_fit_card", inputs=session["selected_item"],
                       returned=session["fit_card"], note="done")
            next_step = None

    return session


def _stop_model_unavailable(session: dict, tool: str, exc: ModelUnavailable) -> None:
    """End the run with a readable message instead of a stack trace."""
    item = session["selected_item"]
    session["error"] = (
        f"Found {item['title']} for ${item['price']:g} on {item['platform']}, "
        f"but the styling model couldn't be reached, so there's no outfit or "
        f"fit card this time.\n  ({exc})"
    )
    trace.step(tool, inputs=item, note="ModelUnavailable, stopping")


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
