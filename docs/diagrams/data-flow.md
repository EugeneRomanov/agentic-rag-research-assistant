```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'background': 'transparent',
  'primaryColor': '#1f1f1f',
  'primaryBorderColor': '#bbbbbb',
  'primaryTextColor': '#ffffff',
  'secondaryColor': '#2a2a2a',
  'tertiaryColor': '#2a2a2a',
  'lineColor': '#e0e0e0',
  'fontFamily': 'Inter, Arial',
  'fontSize': '14px'
}}}%%

flowchart LR

    %% === Input ===
    Query[👤 User Query<br/>"Что такое BERT?"]

    %% === Pipeline ===
    Translate[🌐 Translate<br/>→ English]
    Search[🔎 Search<br/>via MCP]
    Rerank[📊 Rerank<br/>+ entity matching]
    Generate[✍️ Generate<br/>answer + citations]
    Critic[🧪 Critic<br/>verification]
    Answer[✅ Final Answer<br/>with sources]

    %% === Storage / Services ===
    Qdrant[(🗄 Qdrant<br/>Vector DB)]
    LangFuse[(📊 LangFuse<br/>Tracing)]
    Trace[🧾 Trace ID]

    %% === Main Flow ===
    Query --> Translate --> Search
    Search --> Rerank --> Generate --> Critic

    Critic -->|APPROVED| Answer
    Critic -->|REFETCH| Search

    %% === External interactions ===
    Search --> Qdrant

    %% === Observability ===
    Generate --> LangFuse
    Critic --> LangFuse
    LangFuse --> Trace

    %% === Visibility fix ===
    linkStyle default stroke:#e0e0e0,stroke-width:2px
```