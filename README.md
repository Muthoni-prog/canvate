# Glass Jury

**A MeTTa jury assistant that shows its work.**

Track: MeTTa Foundation · Challenge: The Glass Box Agent
State of the Art Hackathon (BASIX.MARKET x SingularityNET), October 2026

Team: Ruth Ndegwa (lead), Lilian Ndolo, Dunson Kimani

---

## What we are building

Art juries decide which works get seen, but the reasons behind those decisions are rarely visible. Artists are rejected without explanation, and in an AI-for-peace show there are extra questions: was AI used, was it disclosed, is the artist's consent on record, and does the work truly fit the theme?

Glass Jury is a MeTTa agent that helps a jury choose artworks for a show like the Harlem Fine Arts Show. It checks each work against explicit rules and returns a verdict of **Selected**, **Needs review**, or **Not selected**. Every verdict comes with the full reasoning trail, and missing information is flagged rather than guessed.

Jurors can **challenge** the agent: change a rule or a weight and watch the rankings update, with the reason for each change. The decision stays with the human jury. The agent makes the reasoning visible so it can be checked, questioned, and trusted before anything is chosen.

## How it works

1. **Input:** a set of artworks described as MeTTa facts (title, artist, theme tags, AI tools used, AI disclosure, consent and rights status, provenance notes).
2. **Hard gates:** missing artist consent, undisclosed AI use, or an unknown rights holder send a work to *Needs review*. Gates never auto-reject a work.
3. **Weighted criteria:** theme fit ("Art as Healing, History as Power, Legacy in Motion"), clear peace or community message, provenance completeness, and originality and process shown.
4. **Output:** a verdict, every rule that fired, flagged gaps, and a confidence level that drops when data is missing.
5. **Challenge loop:** a juror edits a weight or toggles a rule. The agent re-runs and shows which works moved and which rules caused it.

## Project structure

```
/rules.metta     Gates, weighted criteria, explanation trace
/data.metta      Sample artworks as MeTTa facts
/run.py          Thin runner that calls MeTTa and prints the output
/README.md
```

> Update this section to match the actual files in the repo.

## Run it

```
# TODO: add the exact install and run commands once the build is final
# e.g. pip install hyperon
#      python run.py
```

## Demo

- 3-minute video: `TODO: add link`

## Data and permissions

All artworks in `data.metta` are **synthetic sample data** created by the team for this hackathon. No real artist data, HFAS archive material, AI for Peace works, or Incantio catalogue content is used. Any future use of real works requires the rights holder's consent.

> If you use real works, replace this paragraph and name the rights holder who approved it.

## AI disclosure

> Fill this in honestly. List every AI tool the team used and what for.

- Tool: `TODO` used for `TODO` (e.g. brainstorming, drafting README text, debugging code)
- All rules, data, and final code were reviewed by the team.

## Team and roles

| Member | Role |
|---|---|
| Ruth Ndegwa | `TODO` |
| Lilian Ndolo | `TODO` |
| Dunson Kimani | `TODO` |

## Path to market and co-ownership

Glass Jury can be used by juries and curators of shows like HFAS, and by the BASIX job board to explain why a brief or a candidate was selected. In line with the hackathon's co-ownership principles, splits between the builders, BASIX.MARKET, and any go-to-market brokers would be agreed before anything further is built, and consent is a hard gate in the agent itself.

## What's next

- Test on real HFAS or AI for Peace works, with rights holders' consent
- Explanations in Swahili as well as English
- Rule sets for other decisions: licence clearance, royalty splits, provenance checks
- Let juries save, version, and share their rule sets so a decision can be audited later
