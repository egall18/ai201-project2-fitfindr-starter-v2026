# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->



---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Loads all 40 listings and drops any priced above `max_price` or not matching `size`. It scores the rest by keyword overlap with `description` and returns the best matches first. No model call.
  - *Size match:* case-insensitive and token-based, never substring. A listing's size is split on `/`, spaces and parentheses, and the requested size must equal one whole token. `"M"` matches `"S/M"` and `"M/L"` but not `"XL"`. `"8"` matches `"US 8"` but not `"US 8.5"`. `"s"` never matches `"US 9"`. Listings sized `"One Size"` match any requested size.
  - *Score:* each query keyword scores +2 if it appears as a whole word in the title or style tags. Otherwise it scores +1 if it appears in the description, category or colors. Common filler words ("a", "for", "the", "looking"…) are ignored.
- **Inputs:** `description` (str): keywords such as `"vintage graphic tee"`. `size` (str | None): `None` skips size filtering. `max_price` (float | None): an inclusive ceiling; `None` skips price filtering.
- **Returns:** a `list[dict]` of up to `config.SEARCH_RESULT_LIMIT` (10) listing dicts, highest score first. Each dict is a full listing with `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None) and `platform`.
- **When it has nothing:** returns `[]`, an empty list, never `None` and never an exception. That covers every listing being filtered out by price or size, and every listing scoring zero.

### `suggest_outfit`

- **What it does:** Asks the model, through `generate()`, for one or two outfits built around the thrifted item. When the wardrobe has items, the prompt lists each one (name, category, colors, style tags, notes). The model is told to build the outfits from those pieces and name them exactly as written.
- **Inputs:** `new_item` (dict): one listing dict, the item being considered. `wardrobe` (dict): has an `"items"` key holding a `list[dict]` of wardrobe items (`id`, `name`, `category`, `colors`, `style_tags`, `notes`). The list may be empty.
- **Returns:** a non-empty `str` of one or two outfit suggestions. Each one names the new item plus specific wardrobe pieces by their `name`, with one line on why they work together.
- **When it has nothing:** if `wardrobe["items"]` is empty, it still returns a non-empty `str`. The model gives general styling advice for the item (what kinds of pieces, colors and shoes pair with it) and doesn't invent pieces the user owns. If the model comes back blank, the tool returns a short fallback sentence instead of `""`.

### `create_fit_card`

- **What it does:** Asks the model, through `generate()`, for a social-media caption about the find, built from the item and the outfit suggestion. It reads like a real post, not a product description.
- **Inputs:** `outfit` (str): the string `suggest_outfit` returned. `new_item` (dict): the listing dict for the item.
- **Returns:** a `str` of 2–4 sentences that mentions the item, its price (e.g. `$24`) and its platform once each, and is specific about the vibe. The brand is mentioned only when `brand` is not `None`, so a missing brand never leaves a blank in the sentence.
- **When it has nothing:** if `outfit` is empty or only whitespace, it skips the model call and returns a descriptive `str`: `"Couldn't write a fit card for <title>: there was no outfit suggestion to build it from."` It never raises and never returns `""`.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, set `session["error"]` to a message naming what the user could change (raise or drop the price ceiling, try another size, or use broader keywords, depending on which filters were used) and return the session without calling `suggest_outfit` or `create_fit_card`. Otherwise, take the first result as `session["selected_item"]`, pass it to `suggest_outfit`, then pass that outfit and the same item to `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** regex.
- `max_price`: a number after `under`, `below`, `less than`, `max` or a bare `$`, e.g. `under $30` → `30.0`.
- `size`: the word after `size`, e.g. `size M` → `"M"` and `size 8` → `"8"`.
- `description`: whatever is left once those pieces and filler words are removed.

**What moves through the session:** in order:
1. `query`
2. `parsed` (`description`, `size`, `max_price`)
3. `search_results`
4. `selected_item` (always `search_results[0]`)
5. `outfit_suggestion`
6. `fit_card`

`error` is set and the run stops at step 3 if the search comes back empty. Each tool reads its inputs out of the session, not from local variables.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

```

```
$ python -c "from tools import suggest_outfit; ..."

```

```
$ python -c "from tools import create_fit_card; ..."

```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
