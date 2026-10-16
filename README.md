# Glass Jury

**A glass-box jury assistant built in MeTTa.** Glass Jury is a transparent, rule-based decision-support agent. It scores artworks against a jury's rules and shows the full reasoning trail behind every verdict, so jurors can check it, challenge it, and trust it. It supports human jurors; it does not replace them.

*Built for the State of the Art Hackathon (BASIX.MARKET), MeTTa Foundation track, "The Glass Box Agent" challenge. HFAS brief: a jury assistant that shows why an artwork was selected.*

**Demo video:** [[ADD YOUR VIDEO LINK HERE, or delete this line]]

**App Link:**[https://canvate-95appt2qmrbuplfzgbnymxf.streamlit.app/]
## The problem

Art juries and selection panels often cannot explain why one work was chosen over another, and opaque AI scoring makes that worse. Artists and organizers need decisions they can inspect and contest.

## What it does

- Scores each artwork with weighted criteria: theme fit, message, provenance, originality.
- **Hard gates** (artist consent, AI use disclosed, rights holder known). A gate that fails, or cannot be verified, sends the work to **human review**. The agent never auto-rejects.
- **Missing data is flagged as a gap, never guessed**, and confidence is reduced.
- Every verdict comes with a reasoning trail returned by the MeTTa rule `(why $artwork)`.
- **Juror challenge:** change a weight, the threshold, or a gate and see exactly which verdicts move, with a rule change log.

### What kind of AI is this?

Symbolic, rule-based AI for decision support. The rules are written explicitly in MeTTa and applied to facts about each artwork. It does not use machine learning or a language model to make decisions, which is why every step can be shown and challenged.

All reasoning lives in `rules.metta` and `data.metta`. Python only loads files, asks MeTTa questions, and displays the answers.

## Run it

```bash
pip install -r requirements.txt
python run.py            # command-line demo (default rules, then a juror challenge)
streamlit run app.py     # interactive UI
```

You can also upload your own CSV with the columns `id, title, ai_used, ai_disclosed, consent, rights, theme_fit, message, provenance, originality`. A blank cell becomes a gap, not a guess. A sample file is included (`sample_artworks.csv`) and downloadable in the app.

## Try the juror challenge

1. Start with the default rules: 3 works Selected, 5 sent to human review, 4 Not selected.
2. Raise the weight of **originality** from 2 to 4 in the sidebar.
3. Watch **What changed**: *Neon Elders* and *Market Day* become Selected, and the change is recorded in the rule change log.

## Files

| File | Purpose |
|---|---|
| `rules.metta` | Scoring, gates, verdicts, and the `(why ...)` explanation rule |
| `data.metta` | 12 **synthetic** sample artworks |
| `run.py` | Loads MeTTa, parses its answers, converts CSV rows to facts |
| `app.py` | Streamlit interface |
| `sample_artworks.csv` | Example CSV for the upload feature |
| `.streamlit/config.toml` | Theme settings |
| `requirements.txt` | Python dependencies |

## Limits 

- Scoring is simple: weight × a three-level rating (high / medium / low).
- All sample data is synthetic. No real artists, HFAS, AI for Peace or Incantio works are used.
- It only knows the rules and facts it is given. It does not learn.
- It supports human jurors and does not replace them.

## What's next

- Real data, shared with the rights holders' consent.
- A human override that records the juror's reason.
- Working with partners such as HFAS and AI for Peace to match their real selection criteria.

## AI disclosure

 *Claude (Anthropic) was used for brainstorming, planning and debugging the code.The team reviewed and tested all code and data.*

## Team

| Name | Role |
|---|---|
| [Ruth Ndegwa] | [ MeTTa rules and app] |
| [Lilian Ndolo] | [ documentation and README] |
| [Dunson Kimani] | [ Demo Video and README] |