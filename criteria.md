# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
The search is deterministic, so the same query finds the same item every time.
What can vary between tries is the two model calls after it. Each run makes two
requests on the free tier at temperature 0.9, and one of them can come back
rate-limited, blank or unreachable. 5 of 5 would be promising something the
code doesn't control. Below 4 of 5 would mean something is wrong in the loop
itself rather than an occasional bad model call.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path never reaches the model. `search_listings` is plain Python over a
fixed file, and the branch in `run_agent` runs before either model call. Nothing
on this path is random, so the same impossible query has to stop the same way
every time. A single try that goes on to call `suggest_outfit` means the branch
is broken, not unlucky.

---

## 3. The item search found is the item every later tool received

Given a matching query, `session["selected_item"]` has the same `id` as
`session["search_results"][0]`. The trace shows that same item (same title and
price) as the input to both `suggest_outfit` and `create_fit_card`. A try passes
only if all three agree. Target: 5 of 5 tries.

**Why this target:**
Handing the item from one tool to the next is plain Python reading a dict out of
the session, with no model involved. It can't be "mostly right". Either the loop
reads `selected_item` back out of the session, or it passes a stale or
overwritten value. One mismatch is a wiring bug. It would look like a bad outfit
suggestion even though the tool did exactly what it was given.

---

## 4. The fit card is a postable caption about the right item

For the matching query run 5 times with caching off, a fit card passes only if
all four of these hold:
- it is 2–4 sentences long
- it contains the selected item's exact price (e.g. `$24`)
- it names the item's platform (`depop`, `thredUp` or `poshmark`, any case)
- it does not contain the text `None`

Target: at least 4 of 5 tries.

**Why this target:**
The prompt asks for all four, but at temperature 0.9 the model can still drop
the price or run to a fifth sentence, so 5 of 5 isn't something the code can
guarantee. The `None` check is there because 32 of the 40 listings have no
brand, and a prompt that pastes `brand` in blindly would print "None" in the
caption. More than one miss in five would mean the prompt isn't working, not
that the model had an off try.

---

## 5. Search respects the price ceiling and the size, exactly

For `'vintage top size S under $30'`, `session["search_results"]` is non-empty
and every listing in it passes both of these:
- priced at or below $30
- has `S` as a whole size token (`S`, `S/M`) or is `One Size`

No `US 7`, `US 9` or `XL (fits oversized)`, all of which contain the letter s.
Target: 5 of 5 tries.

**Why this target:**
The size strings in this data are traps for a substring test. `"s"` is inside
`"US 9"`, `"One Size"` and `"XL (fits oversized)"`, and a search that returns
shoes for a small top reads as broken even when every later step works.
`search_listings` makes no model call, so the same query must give the same
filtered results every time. Anything less than 5 of 5 is a bug in the filter.
---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
