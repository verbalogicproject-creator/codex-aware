# Product Demonstration — 2:45

This is a product demonstration. Do not mention judging, scoring, Build Week, or hackathon constraints in the recording.

## 0:00–0:08

Show the four-project graph.

Voice: “Point at your running software. Codex already knows what you mean.”

## 0:08–0:30

Select Team Todo `delete_task` and Battleship `fire_at`.

Voice: “These come from different applications. I have selected them visually—no file paths, no copied code.”

## 0:30–0:52

Switch to Codex or ChatGPT Android and ask: “What is happening here?”

Voice: “The applications supply stable identity, source location, runtime relationships, and current authority. The model does not have to rediscover what ‘these’ means.”

## 0:52–1:12

Request “Reveal the blast radius.” Return to the graph as affected nodes illuminate.

Voice: “This is a semantic action, not a generated click. The receipt is still pending until the browser observes the effect.”

## 1:12–1:40

Show the safety difference and request the classification proposal.

Voice: “Both commands mutate state. Battleship declares runtime guards. Team Todo’s imported delete command has no application-neutral safety policy.”

Approve once in the browser.

## 1:40–2:05

In Codex, patch the two adapter fields. Run:

```bash
python scripts/check_policy.py examples/team-todo/aware.yaml --require-protected
```

Call `aware_refresh`.

## 2:05–2:25

Show amber becoming green and open the final receipt.

Voice: “Selection, grounding, human authority, diff, test, refresh, and observed effect are one causal record.”

## 2:25–2:37

Open the receipt’s architecture graph.

Voice: “The same graph can explain the resolver, gate, directive, database, observer, and test that made the result trustworthy.”

## 2:37–2:45

Show the origin artifact briefly, then return to the product.

Voice: “When software can describe itself through the same surface by which it is safely controlled, intelligence becomes attachable rather than embedded.”

