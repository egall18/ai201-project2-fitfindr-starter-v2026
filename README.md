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

FitFindr takes a plain-language thrift request like `'vintage graphic tee under $30'`
or `'90s track jacket in size M'` and searches 40 secondhand listings from
depop, thredUp and poshmark for the best match within the price and size you
gave. For the top match, it suggests one or two outfits built from pieces
already in your saved wardrobe, or general styling advice if the wardrobe is
empty. It then writes a short, postable caption (a "fit card") with the item,
its price and its platform. If nothing matches, it stops before calling the
model and tells you which filter to loosen.


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
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1
Y2K Baby Tee — Butterfly Print
Baggy straight-leg jeans, dark wash
Chunky white sneakers
Black crossbody bag

Why it works: The fitted crop balances the baggy denim for a classic 2000s streetwear silhouette, and the white sneakers tie in the tee's base color.


Outfit 2
Y2K Baby Tee — Butterfly Print
Wide-leg khaki trousers
Vintage black denim jacket
Black combat boots
Brown leather belt

Why it works: The pastel butterfly graphic softens the utilitarian khaki trousers, while the black jacket and boots add a nice edge to the look.

  Fit card: Found the ultimate Y2K baby tee with the cutest pastel butterfly graphic. It's listed on depop for $18 and looks so good balanced out with baggy dark wash jeans and chunky sneakers. Perfect little cropped top for channeling that early 2000s streetwear energy.

0 model calls this session, 2 served from cache
```

The same loop on a query nothing can match stops at the branch, with no model calls:

```
$ python app.py ask 'designer ballgown size XXS under $5'

  Nothing matched 'designer ballgown' in size XXS under $5. Try to raise your budget above $5, drop the size XXS filter, or use broader keywords (e.g. 'dress' instead of a specific style).

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit 1:
- Vintage Levi's 501 Jeans — Medium Wash
- White ribbed tank top
- Oversized grey crewneck sweatshirt
- Chunky white sneakers
- Black crossbody bag
Why it works: Tucking the white tank into the straight 501s and layering the oversized crewneck creates a classic, effortless streetwear silhouette anchored by chunky sneakers.

Outfit 2:
- Vintage Levi's 501 Jeans — Medium Wash
- Black cropped zip hoodie
- Black combat boots
- Brown leather belt
Why it works: The cropped hoodie highlights the waist of the vintage denim, while the black boots and belt tie the edgy streetwear elements together.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Nothing beats broken-in Levi's with that exact fade at the knees. Paired them with crisp white sneakers for that effortless run-errands-and-get-iced-coffee look. Grab them on depop for $38 before I change my mind and keep them.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* A regex `parse_query` for `run_agent` that pulls `max_price`, `size` and `description` out of the user's query, with whatever's left over becoming the description.
- *What came back:* It got the price and size right on every example query. But the leftover description kept filler at the edges: `'90s track jacket in size M'` became `'90s track jacket in'`, and `'leather bomber $80 max'` became `'leather bomber max'`. Search was fine, because `search_listings` already ignores those words. The problem was that the no-results message quotes the description back to the user, so they would have seen "Nothing matched '90s track jacket in'".
- *What I changed:* Added `_EDGE_FILLER` and a trim in `agent.py::parse_query` that strips filler words off both ends of the description. Re-ran the parser: those queries now come out as `'90s track jacket'` and `'leather bomber'`.

**Moment 2**

- *What I asked for:* `create_fit_card` built to the Tool Inventory spec: guard an empty outfit, build the prompt, return the caption.
- *What came back:* The empty-outfit guard was there, but the function returned `generate()`'s text directly. `generate()` returns `(response.text or "").strip()`, so a blank model reply would come back as `""`. My Tool Inventory says this tool never returns `""`. The prompt part was right as it came back: `_describe_item` already leaves the brand line out when `brand` is `None`, which matters because 32 of the 40 listings have no brand.
- *What I changed:* Added a fallback message for a blank model reply, matching the one in `suggest_outfit`, so the function's behaviour matches what the README promises. Then tested on a no-brand listing (`lst_006`): the card contains `$24` and `depop`, and no `None`.

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
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search found is the item every later tool received | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card is a postable caption about the right item | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Search respects the price ceiling and the size, exactly | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

`python run_eval.py --label before` →
[results/run_2026-10-07_1815_before.md](results/run_2026-10-07_1815_before.md).
Caching was off: 50 real model calls, 0 served from cache, and all five outfits
and all five fit cards differ from each other in every scenario that reaches the
model. The empty-wardrobe scenario is a diagnostic run (not one of the five). It
completed all 5 tries with general styling advice and a fit card.

**Real output from one try**, pasted as text, naming the file and function
that produced it. This is criterion 4, try 1: the loop in `agent.py::run_agent`,
called by `run_eval.py::run_once`. The caption is from `tools.py::create_fit_card`.

```
query: vintage graphic tee under $30   (example wardrobe, caching off)

[1] parse_query (regex)
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    branch: results, selected_item = search_results[0]
[3] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Outfit One Y2K Baby Tee — Butterfly Print Baggy straight-leg jeans, dark wash Chunky white sneakers Black cros…
      →    wardrobe: 10 items
[4] create_fit_card
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Found the ultimate Y2K baby tee with the sweetest little butterfly print. It's up on my depop right now for $1…
      →    done

Fit card:
Found the ultimate Y2K baby tee with the sweetest little butterfly print. It's up on my depop right now for $18. I love balancing the cropped fit with baggy dark wash jeans and chunky sneakers for that classic early 2000s streetwear look.
```

3 sentences, the exact price `$18`, the platform `depop`, and no `None`, so it
passes all four parts of criterion 4. The brand is `None` for this listing.

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
| 1 | A matching query completes all three tools | 4 of 5 | MET (5/5) | Every try has `session["error"]` as `None`, a non-empty `fit_card`, and `search_listings (via MCP)`, `suggest_outfit` and `create_fit_card` all in its trace. The rate limiter paused the run 3 times, but no try failed. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | Every try has an `error` naming what to change ("raise your budget above $5, drop the size XXS filter…"). `outfit_suggestion` and `fit_card` are `None`, and the trace ends at step 2 with no `suggest_outfit`. |
| 3 | The item search found is the item every later tool received | 5 of 5 | MET (5/5) | In every try `selected_item["id"]` equals `search_results[0]["id"]` (`lst_004`). The trace's `in:` line for both `suggest_outfit` and `create_fit_card` reads exactly `90s Track Jacket — Navy/White Stripe ($45.0, poshmark)`. |
| 4 | The fit card is a postable caption about the right item | 4 of 5 | MET (5/5) | Every card is 2–3 sentences and contains `$18` and `depop`. None contains `None`, even though this listing's brand is `None`. |
| 5 | Search respects the price ceiling and the size, exactly | 5 of 5 | MET (5/5) | Every try returns the same 5 results: all $30 or less, sized `S/M`, `One Size` or `One Size (adjustable)`. No `US 7`, `US 9` or `XL (fits oversized)`. |

I scored every try with a script that checks each criterion's wording against
the saved session and trace, then read the cards myself. One correction on the
way: the script first failed all five tries of criterion 5 because it only
counted the exact string `One Size`, not `One Size (adjustable)`. The criterion
says "or is `One Size`", and that listing is. The scorer was wrong, not the
search, so I fixed the scorer and left the criterion as written.

**Diagnoses**

No criterion missed, so there is no miss to diagnose. The output still has one
pattern that the criteria don't measure, and it is the weakest part of the run.

**The fit cards share one template. Place: the model's output, caused by the
`tools.py::create_fit_card` prompt.** Across all 25 cards in the run (three
different items), 23 open with "Found…": 14 with "Found the ultimate", and 4
more with "Found this vintage". 10 of 25 end on the same seller line, "before I
change my mind and keep it" or "before I keep it for myself". This isn't one
item repeating itself. The Champion track jacket and the Wrangler denim jacket
open with "Found" 4 of 5 times each, the same as the tee. It isn't the cache or
the temperature either: caching was off and no two cards are identical. The
model varies the middle of the caption and keeps the frame.

The mechanism: the prompt says what a card must *contain* (2–4 sentences, the
price and platform once each, a brand only if listed) but nothing about how it
should *open or close*. Its framing, "captions for thrift finds" in the system
message and "a post about this thrift find" in the prompt, points to "Found…" as
the most likely first word. With no instruction against it, temperature 0.9
only reshuffles the words after it.

Criterion 4 didn't catch this because it scores each card on its own, and every
card on its own is fine. The repetition only shows when you read them side by
side, which is exactly what a follower scrolling past several posts would do.



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
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query (regex)
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    branch: results, selected_item = search_results[0]
[3] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Outfit 1 Y2K Baby Tee — Butterfly Print Baggy straight-leg jeans, dark wash Chunky white sneakers Black crossb…
      →    wardrobe: 10 items
[4] create_fit_card
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Found the ultimate Y2K baby tee with the cutest pastel butterfly graphic. It's listed on depop for $18 and loo…
      →    done
```

**Empty search**

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query (regex)
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit

  Nothing matched 'designer ballgown' in size XXS under $5. Try to raise your budget above $5, drop the size XXS filter, or use broader keywords (e.g. 'dress' instead of a specific style).

0 model calls this session
```

The empty search stops after step 2, two steps shorter than the happy path,
with 0 model calls.

**On the MCP move:** `search_listings` is registered in `mcp_server.py`, and
`agent.py::run_agent` now calls it with `call_tool("search_listings", {...})`
instead of importing it. Before the swap, I ran the direct function and the MCP
call side by side on seven queries: three that match, two size traps (`size S`
and `size 8`), and three that return nothing. All seven came back identical,
down to the field types. Empty searches arrive as `[]`, not `None`, and a
missing brand arrives as `None`, so the branch didn't need to change. The only
behavior difference is speed: each call starts and stops the server, which adds
about 2 seconds per search. The move also adds a new way to fail, so
`run_agent` catches `MCPError`. I pointed the client at a server file that
doesn't exist, and the run stopped at step 2 with "The listing search couldn't
be reached, so nothing was searched" instead of a traceback.

**Failure modes, triggered on purpose**

| Failure | How I triggered it | What happens now |
|---|---|---|
| Empty search | `python app.py ask 'designer ballgown size XXS under $5'` | The branch stops after `search_listings` with a message naming the filters to loosen. 0 model calls (trace above). |
| Empty wardrobe | `python app.py ask 'vintage graphic tee under $30' --empty-wardrobe --trace` | `suggest_outfit` gives general styling advice without claiming the user owns anything. The trace notes `wardrobe: empty, general styling advice`, and the run still finishes with a fit card. |
| Model unreachable | One character of the API key changed, cache off (`AI201_CACHE=0`) | Before the fix, `run_agent` raised `ModelUnavailable` out of `tools.py::suggest_outfit` as a traceback and returned no session. Now it catches the error, keeps the item it found and stops (trace below). |

```
$ AI201_CACHE=0 python app.py ask 'vintage graphic tee under $30' --trace   # key off by one character
[1] parse_query (regex)
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    branch: results, selected_item = search_results[0]
[3] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    ModelUnavailable, stopping

  Found Y2K Baby Tee — Butterfly Print for $18 on depop, but the styling model couldn't be reached, so there's no outfit or fit card this time.
  (The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.)

1 model calls this session
```



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** two rules added to the end of the prompt in
`tools.py::create_fit_card`, and nothing else:

```
- Don't open with "Found" or any line about finding or thrifting it. Open on a detail of the item or on how it's being worn.
- Don't close with "before I change my mind", "keep it for myself" or any other line about keeping it.
```

The system message, the "thrift find" framing, the temperature and every other
rule stayed the same, so the after-run measures these two lines only. I
smoke-tested once before the measured run (cache off, one call). The opener rule
worked on that try, but the closer, which I had first written as "a line about
keeping it for yourself or changing your mind", still ended "before I change my
mind". So I quoted the exact phrases, the same way the opener rule quotes
"Found", before running the eval.

**Which failure it was meant to fix:** the template diagnosed above. The prompt
said what a card must contain but not how to open or close it, so 23 of 25
cards opened with "Found…" and 10 of 25 closed on "before I change my mind / keep
it for myself".

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search found is the item every later tool received | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card is a postable caption about the right item | 4 of 5 | PASS | FAIL | FAIL | PASS | FAIL | **MISSED (2/5)** |
| 5. Search respects the price ceiling and the size, exactly | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

`python run_eval.py --label after` →
[results/run_2026-10-07_1827_after.md](results/run_2026-10-07_1827_after.md).
Caching was off: 44 real model calls.

**Did it help, and how do I know:**

On the failure it targeted, the opener, yes, completely. On the closer, only
partly. And the run log got worse for a reason the change didn't cause.

| Measured on every fit card in the run | Before (25 cards) | After (19 cards) |
|---|---|---|
| Opens with "Found…" | 23 | **0** |
| Opens with "Found the ultimate" | 14 | **0** |
| Closes on "change my mind" / "keep it for myself" | 10 | **0** |
| Closes on "…before someone else snags it / does" | 0 | 6 |
| Passes all four criterion-4 format checks | 25 / 25 | 19 / 19 |

- **The opener is fixed.** No card starts with "Found" now. They open on the
  item ("That pastel butterfly graphic…", "Structured shoulders…", "The crisp
  white sleeve stripes…"). This holds across all three items, not only the tee.
- **The closer moved instead of going away.** The quoted phrases are gone, but
  6 of 19 cards now end on a new urgency line, "before someone else snags it".
  Counting any "grab it before…" closer, that's 10 of 25 (40%) before and 6 of 19
  (32%) after. Banning specific words just pushed the model to the next most
  likely sign-off.
- **The format didn't break.** Every card that was written still passes all four
  criterion-4 checks (2–4 sentences, exact price, platform, no `None`).
- **Criterion 4 went from MET 5/5 to MISSED 2/5, and the change isn't why.**
  The three failed tries (2, 3 and 5) wrote no card at all. Each stopped at step
  3, `suggest_outfit`, which runs *before* `create_fit_card` and wasn't touched,
  with the same error:

  ```
  Found Y2K Baby Tee — Butterfly Print for $18 on depop, but the styling model couldn't be reached, so there's no outfit or fit card this time.
    (Couldn't reach the model: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}})
  ```

  Criterion 5's scenario hit the same 503 on tries 2, 3 and 5. They passed only
  because criterion 5 checks the search, which had already finished. All six
  503s came in the last two scenarios. Place: the model, then the adapter. The
  mechanism: `generate.py` retries only rate-limit errors (`429`, "resource
  exhausted"), so a 503 "high demand" error becomes `ModelUnavailable` on the
  first attempt with no retry. The Milestone 2 handler then did its job: a
  message, not a crash. This is the "unreachable" case criterion 1's reason said
  could happen. It hit criterion 4's scenario instead, and three times rather
  than once.

I kept the miss rather than re-running until the 503s went away. Re-running
until it passes would make this table say something that didn't happen.



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

**Criterion 4 is still MISSED (2/5 in the after-run), because a busy model
isn't retried.** The three failed tries never got to write a card. `suggest_outfit`
got `503 UNAVAILABLE` ("This model is currently experiencing high demand"), and
`generate.py::generate` treats anything that isn't a rate limit as fatal. Its
retry rule only checks for `429`, "resource exhausted" or "rate limit", so a 503
raises `ModelUnavailable` on the first attempt, even though the error itself
says "Spikes in demand are usually temporary". **What I'd do:** count `503` /
`unavailable` as retryable in that same `rate_limited` check, so it goes through
the existing backoff (up to `MAX_RETRIES`, 5 attempts) before giving up. A bad
key would still fail fast: it returns `401 UNAUTHENTICATED`, which I checked
with the same off-by-one key from Milestone 2. Then re-run `--label after` to see whether
criterion 4 returns to at least 4 of 5. **Why I stopped:** Milestone 5 is one
change, measured on its own. Fixing the retry in the same run would have mixed
two causes in one table, and I couldn't have said which one moved criterion 4.
The miss also isn't caused by anything in my loop. It's the model being
overloaded, and my handler already turns it into a readable message rather than
a crash.

**The fit card closer moved instead of going away.** This isn't a criterion
miss: all 19 after-run cards pass criterion 4's format checks. But banning
"before I change my mind" and "keep it for myself" just made "before someone
else snags it" the new default (6 of 19). A list of banned phrases will keep
losing to whatever the next most likely sign-off is. **What I'd do:** give the
last sentence a job instead of a ban, for example "end on one styling detail
from the outfit". Or drop the seller framing ("captions for thrift finds") from
the system message, since that framing is what invites urgency lines. Then
measure it the same way, counting closers across all cards. **Why I stopped:**
same reason, one change per measured run, and the opener (23/25 → 0/19) was the
bigger half of the template.

**Criterion 4 can't see repetition.** It scores each card on its own, so it
stayed MET 5/5 in the before-run while 23 of 25 cards opened the same way. I
found the template by reading the cards side by side, not from the table. It
isn't broken under this unit's rule, since it measures exactly what it says, so
I left it as written. **What I'd do next unit:** add a separate criterion that
scores the set, such as "across 5 tries on 3 different items, no two cards share
their first three words". That way the next template shows up in the run log
instead of in my reading.



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
