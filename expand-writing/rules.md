# Style rules for `expand-writing`

> Rules in this file are adapted from *The Elements of Agent Style*
> (https://github.com/yzhao062/agent-style), © Yue Zhao and contributors,
> licensed under CC BY 4.0. Modifications: condensed and reformatted for use
> inside a Claude Code skill.

Each rule has a short ID so the skill's change log can cite it.

## R01 — Name the reader

Before rewriting a sentence, know who reads it. Pick register, vocabulary, and what can be assumed from the audience description, not from the training corpus default.

- Do: ground every phrasing choice in the stated audience.
- Don't: drift to near-expert register just because the training data does.

## R03 — Specific over vague

Replace *various*, *several*, *some*, *many*, *a number of* with a concrete number, name, or date when the input supports it. If it does not, flag the gap in the change log rather than making one up.

- Do: "three benchmarks (GLUE, SuperGLUE, MMLU)"
- Don't: "several benchmarks"

## R04 — Cut filler

Strike stock filler phrases:

- *in order to* → *to*
- *due to the fact that* → *because*
- *may potentially* → *may*
- *it should be noted that* → (delete)
- *at this point in time* → *now*
- *in the event that* → *if*

## R06 — Plain verbs

Prefer short plain verbs over corporate synonyms.

- *use*, not *utilize* / *leverage*
- *method*, not *methodology* (reserve *methodology* for the study of methods)
- *start*, not *commence*
- *help*, not *facilitate*
- *show*, not *demonstrate* (unless a proof)
- *end*, not *terminate*

## R08 — Match verb to evidence

The strength of the claim must match the strength of the evidence.

- *suggest / indicate* — soft evidence, small effect, early signal.
- *show / find* — supported by the reported experiments.
- *prove / establish* — formal proof or overwhelming evidence.

Do not auto-hedge certain findings into *may suggest*; do not inflate a single data point into *proves*.

## R11 — Stress position

Put the new or most important information at the end of the sentence; put the familiar/linking material at the front.

- Do: "On the same benchmark, our method reduces error by 23%."
- Don't: "Our method reduces error by 23% on the same benchmark."

## R12 — Sentence length

Break any sentence over ~30 words. Vary short and long. A one-clause sentence after a long one is a tool, not a mistake.

## RA — Prose over bullets

Use bullets only for genuinely parallel lists (three or more items of the same kind). Do not bullet-ize a paragraph that already flows.

## RB — Punctuation

Prefer commas, colons, and parentheses. Use em-dashes sparingly and only to mark a genuine aside; do not use them as stylistic filler between two normal clauses. Never space-pad em-dashes.

## RF — Acronyms

Define every acronym on first use (*Large Language Model (LLM)*), then use the acronym consistently. Do not redefine. Do not switch between the acronym and the long form in the same document without reason.

## RH — Named citations and concrete numbers

Never write *prior work shows* or *it has been shown*. Cite a named work, a named person, or a concrete number. If the input draft lacks one, flag it in the change log — do not invent a citation.

## RI — Full forms

No contractions in technical prose: *do not* (not *don't*), *it is* (not *it's*), *cannot* (not *can't*). For conversational audiences (register: conversational), contractions are allowed.
