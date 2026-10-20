# Glass Jury

**A glass-box jury assistant built in MeTTa.** Glass Jury is a transparent, rule-based decision-support agent. It scores artworks against a jury's rules and shows the full reasoning trail behind every verdict, so jurors can check it, challenge it, and trust it. It supports human jurors; it does not replace them.

*Built for the State of the Art Hackathon (BASIX.MARKET), MeTTa Foundation track, "The Glass Box Agent" challenge. HFAS brief: a jury assistant that shows why an artwork was selected.*

**Demo video:** [ADD YOUR VIDEO LINK HERE]

**Live app:** [https://canvate-95appt2qmrbuplfzgbnymxf.streamlit.app/](https://canvate-95appt2qmrbuplfzgbnymxf.streamlit.app/)

## Track and challenge

- **Track:** 02 Builders, MeTTa Omega
- **Level:** MeTTa Foundation (Level 1)
- **Challenge:** The Glass Box Agent. Every decision comes with a reasoning trail anyone can challenge.

> **Note on the brief:** the HFAS "jury assistant" brief is a challenge concept pending partner sign-off. Glass Jury is built to the challenge description, not to any confirmed HFAS requirement. All data is synthetic.

## The problem

Art juries and selection panels often cannot explain why one work was chosen over another, and opaque AI scoring makes that worse. Artists and organizers need decisions they can inspect and contest.

## What it does

- **Scores** each artwork on weighted criteria: theme fit, message, provenance, originality.
- **Hard gates** (artist consent, AI use disclosed, rights holder known). A gate that fails, or cannot be verified, sends the work to **human review**. A gate never rejects a work on its own.
- **Missing data is flagged as a gap, never guessed.** Confidence is reduced. If a gap could change the outcome (the work would pass with a top rating), the work goes to human review. If it could not, the work is not selected and the reason says so.
- **Every verdict comes with a reasoning trail** returned by the MeTTa rule `(why $artwork)`, including how far above or below the threshold the score is (the *margin*).
- **Juror challenge to the rules:** change a weight, the threshold or a gate, and see exactly which verdicts move, with a rule change log.
- **Juror challenge to one verdict:** record a **human decision with a required reason**. The machine verdict stays visible beside it, and the decision is stored as a MeTTa atom.
- **Close calls:** for every work whose gates are clear, MeTTa lists the single rating steps that would change the verdict, for example "raising message from medium to high (+2) would reach the threshold". Works one step from a different verdict are flagged, so jurors know where to look twice.
- **Consistency checks on human decisions:** if a juror selects a work that scores lower than a work left out, or selects a work despite a failed or unverifiable gate, the app flags it and the audit file records it.
- **The rules, on screen:** the whole decision logic (`rules.metta`) is shown inside the app. There is nothing else behind the screen.
- **Audit trail:** download one JSON file with the rules in force, every verdict and its reasoning trail, every human decision, and the change log.

### What kind of AI is this?

Symbolic, rule-based AI for decision support. The rules are written explicitly in MeTTa and applied to facts about each artwork. It does not use machine learning or a language model to make decisions, which is why every step can be shown and challenged.

## How it works

```
data.metta (facts)  ──┐
                      ├─►  rules.metta (MeTTa)  ──►  (why $artwork)  ──►  run.py parses  ──►  app.py draws
rules.metta (rules) ──┘     verdict, score,            the reasoning        atoms into          the screen
juror changes as atoms      gates, gaps, margin,       trail, one atom      rows
(weights, gates,            human decisions            per fact
threshold, decisions)
```

All reasoning lives in `rules.metta` and `data.metta`. Python only loads files, asks MeTTa questions, and displays the answers. MeTTa features used:

- **Pattern matching** (`match`, `unify`) to find facts and detect gaps (a fact that is *not* there).
- **Equations with several definitions** for `(violates $a $gate)` and `(why $a)`, so each reason is its own small rule.
- **Aggregation** (`collapse`, `foldl-atom`) to total the score and the best-case points a gap could add.
- **Non-determinism** (`superpose`, `collapse`) so one rule can return a whole family of facts: all the single rating steps that would flip a verdict.
- **Atoms as live state:** `add-atom` and `remove-atom` change weights, gates, the threshold and human decisions. Each browser session gets its own MeTTa space.

The verdict rule, in plain words:

1. A gate failed or cannot be verified: **needs review**.
2. Score reaches the threshold: **selected**.
3. Score is short, but the gaps could still close it: **needs review**.
4. Score is short and the gaps cannot close it: **not selected**.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                        # command-line demo (default rules, a rule challenge, a human decision)
streamlit run app.py                 # interactive UI
```

You can also upload your own CSV with the columns `id, title, ai_used, ai_disclosed, consent, rights, theme_fit, message, provenance, originality`. A blank cell becomes a gap, not a guess. A sample file is included (`sample_artworks.csv`) and downloadable in the app. No API keys or secrets are needed.

## Test it

```bash
pip install -r requirements-dev.txt
pytest
```

The 38 tests check the default split, every gate state, the gap rule, the margin, close calls (including that a suggested change really flips the verdict), the originality challenge, human decisions and their consistency checks (including bad input), CSV handling, and the running Streamlit app. They take a few minutes.

## Try the juror challenge

1. Start with the default rules: **3 Selected, 6 sent to human review, 3 Not selected.**
2. Look at *Neon Elders*: it is **1 point short** of the threshold (margin −1).
3. Look at *Quiet Harvest*: its originality is missing. It scores 16, but a top rating would give 22, so it goes to a human instead of being guessed.
4. Raise the weight of **originality** from 2 to 4 in the sidebar. *Neon Elders* and *Market Day* become Selected (now 5 / 6 / 1), and the change is recorded in the rule change log.
5. Note the banner **"2 close calls"**: *Neon Elders* (1 point short) and *Open Door Quilt* (1 point above). Open **Why?** on *Neon Elders* to see which single rating change would select it.
6. Record a **human decision** on *Market Day* (Selected, with a reason). The app warns that *Neon Elders* scores higher but was not selected, so the jury must be ready to explain the difference.
7. Download the **audit trail**.

## Can a jury trust it?

A real jury or a real artist should be able to answer yes to each of these, and each one is checked by a test or visible on screen:

| Question | Answer |
|---|---|
| Can I see why a work got its verdict? | Yes. Every verdict has a trail returned by `(why $artwork)`, shown in the app as the raw MeTTa atoms. |
| Can I see the rules themselves? | Yes. `rules.metta` is displayed inside the app. |
| Does it guess when facts are missing? | No. A blank cell is a gap, and the system only asks whether the gap could matter. |
| Can it reject someone because paperwork is missing? | No. A failed or unverifiable gate sends the work to a person. |
| Can a person overrule it? | Yes, with a required reason. The machine verdict stays visible. |
| Will anyone notice an inconsistent human decision? | Yes. The app flags a higher-scoring work left out, and a hard gate overruled. |
| Does it show which verdicts are fragile? | Yes. Close calls name the exact rating step that would change the result. |
| Does my data leave my browser session? | No. Nothing is sent to an AI service, and no key is needed. |
| Is it the same answer every time? | Yes. It is deterministic rules, with no model and no randomness. |
| Is the behaviour tested? | Yes. 38 automated tests cover the rules, the CSV import and the running app. |

## Decisions we made

- **A gate never auto-rejects.** A missing consent, undisclosed AI use or unknown rights holder is a question for a person, not a reason to discard a work.
- **A gap is never filled in by the machine.** We only ask whether the gap *could* change the outcome, and if so, a human looks.
- **A human decision never overwrites the machine verdict.** Both are shown, so anyone can see where the jury departed from the rules and why.
- **Every explanation is produced by MeTTa**, not written in Python. The screen cannot say something the rules did not.

## Files

| File | Purpose |
|---|---|
| `rules.metta` | Scoring, gates, gaps, margin, verdicts, close calls, human decisions, consistency checks, and the `(why ...)` explanation rule |
| `data.metta` | 12 **synthetic** sample artworks |
| `run.py` | Loads MeTTa, parses its answers, converts CSV rows to facts |
| `app.py` | Streamlit interface |
| `tests/` | Automated tests for the rules and the app |
| `sample_artworks.csv` | Example CSV for the upload feature |
| `.streamlit/config.toml` | Theme settings |
| `requirements.txt`, `requirements-dev.txt` | Python dependencies (run, and run plus test) |
| `AI_DISCLOSURE.md` | Which AI tools were used, and for what |
| `LICENSE` | MIT licence |
| `.env.example` | States that no secrets are needed |

## Limits

- Scoring is simple: weight × a three-level rating (high / medium / low).
- All sample data is synthetic. No real artists, HFAS, AI for Peace or Incantio works are used.
- It only knows the rules and facts it is given. It does not learn, and it does not use Omega yet.
- Close-call analysis changes one rating at a time. It does not search combinations.
- Human decisions live for the browser session and are exported in the audit file. They are not stored on a server.
- It supports human jurors and does not replace them.

## What's next

- Real data, shared with the rights holders' consent.
- Saving human decisions between sessions, with the juror's name.
- Working with partners such as HFAS and AI for Peace to match their real selection criteria.
- Letting a jury add its own criteria and gates as new MeTTa rules.
- Moving the agent onto Omega, so it remembers past juries and corrections between sessions.

## AI disclosure

Claude (Anthropic) was used for brainstorming, planning, writing and debugging code, tests and documentation. The team reviewed and tested all code and data. Glass Jury itself uses no AI model to make decisions. Full details: [AI_DISCLOSURE.md](AI_DISCLOSURE.md).

## Built with, and licence

Built with [Hyperon / MeTTa](https://github.com/trueagi-io/hyperon-experimental), [Streamlit](https://streamlit.io) and [pandas](https://pandas.pydata.org). These open-source libraries keep their own licences. Our code is released under the MIT licence (see `LICENSE`). As set out in the hackathon rules, the team keeps authorship of this code, and any incubation or commercial terms are agreed separately in writing.

## Team

| Name | Role |
|---|---|
| Ruth Ndegwa | MeTTa rules and app |
| Lilian Ndolo | Documentation and README |
| Dunson Kimani | Demo video and README |
