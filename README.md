# Music4u — AI Music Recommender

An AI-powered music recommendation system that combines a deterministic scoring engine with Claude LLM for natural language understanding, retrieval-augmented generation (RAG), and agentic self-evaluation.

---

## System Architecture

```mermaid
flowchart TD
    A([👤 Human User])

    subgraph UI["Streamlit Web UI"]
        B[Natural Language\nText Input]
        N[Results Display\nRanked Songs + Explanations]
    end

    subgraph NLU["Claude — NL Understanding"]
        C[Parse Natural Language\nClaude API Call]
        D[Structured User Profile\ngenre · mood · energy · tempo ...]
    end

    subgraph RAG["Retrieval Layer — RAG"]
        E[(songs.csv\n18-song catalog)]
        F[Scoring Engine\nrecommender.py · score_song]
        G[Top-K Songs Retrieved\nwith scores + features]
    end

    subgraph GEN["Claude — Generation"]
        H[Build RAG Context\nUser query + retrieved songs]
        I[Claude API\nGenerate Personalized Explanations]
    end

    subgraph AGENT["Agentic Evaluation Loop"]
        J[Claude Self-Evaluator\n'Do these match the request?']
        K{Quality Check}
        L[Re-rank / Adjust Criteria]
    end

    subgraph LOG["Logging & Guardrails"]
        O[Session Logger\nlogs/*.log]
        P[Fallback Mode\nscoring-only if Claude unavailable]
    end

    subgraph TEST["Testing & Reliability"]
        Q[Unit Tests\n21 pytest tests · scoring logic]
        R[Eval Script\nend-to-end quality checks]
        S([👤 Human Review\nof edge cases])
    end

    A --> B
    B --> C
    C --> D
    D --> F
    E --> F
    F --> G
    G --> H
    D --> H
    H --> I
    I --> J
    J --> K
    K -->|Pass| N
    K -->|Fail| L
    L --> F
    N --> A

    C --> O
    I --> O
    J --> O
    O --> P
    P --> F

    Q -.->|validates scoring| F
    R -.->|validates output| N
    S -.->|reviews results| R
```

---

## Data Flow Summary

| Step | Component | What Happens |
|------|-----------|--------------|
| 1 | **Human User** | Types a natural language request |
| 2 | **Streamlit UI** | Accepts input, displays final results |
| 3 | **Claude NLU** | Parses text → structured preference profile |
| 4 | **Scoring Engine** | Scores all 18 songs against the profile |
| 5 | **RAG Retrieval** | Top-K songs retrieved with features |
| 6 | **Claude Generation** | Uses retrieved songs to write explanations |
| 7 | **Claude Evaluator** | Self-checks if recommendations fit the request |
| 8 | **Quality Check** | Pass → display · Fail → re-rank and retry |
| 9 | **Logger** | Records every API call, score, and error |
| 10 | **Fallback** | Scoring-only mode if Claude is unavailable |

---

## Advanced AI Features

| Feature | Implementation |
|---------|---------------|
| **RAG** | Song catalog retrieved before Claude generates explanations |
| **Agentic Workflow** | Claude evaluates its own output and triggers re-ranking if needed |
| **Logging & Guardrails** | All sessions logged; fallback to scoring-only on API failure |
| **Reliability Testing** | Unit tests (scoring math) + eval script (end-to-end) + human review |

---

## Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd applied-ai-music-recommender-project

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Anthropic API key
export ANTHROPIC_API_KEY=your_key_here

# 5. Run the Streamlit app
streamlit run src/app.py

# 6. Or run the CLI demo
python src/main.py

# 7. Run tests
pytest tests/
```
