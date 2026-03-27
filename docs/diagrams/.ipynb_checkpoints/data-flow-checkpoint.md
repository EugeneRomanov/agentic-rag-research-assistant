```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'background': '#ffffff',
  'primaryColor': '#ffffff',
  'primaryBorderColor': '#000000',
  'primaryTextColor': '#000000',
  'lineColor': '#000000',
  'fontFamily': 'arial',
  'fontSize': '14px'
}}}%%

graph LR
    Query[User Query<br/>"Что такое BERT?"] --> Translate[Translate to English<br/>"What is BERT?"]
    Translate --> Search[Search Qdrant<br/>via MCP]
    Search --> Qdrant[(Qdrant<br/>100 articles, 3369 chunks)]
    Search --> Rerank[Rerank by relevance<br/>+ entity matching]
    Rerank --> Generate[Generate answer<br/>with citations]
    Generate --> Critic[Verify with Critic]
    Critic -->|APPROVED| Answer[Answer with citations<br/>+ sources]
    Critic -->|REFETCH| Search
    
    Generate --> LangFuse[(LangFuse<br/>Traces)]
    Critic --> LangFuse
    LangFuse --> Trace[Trace ID]
    
    classDef white fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000
    classDef storage fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000
    
    class Query,Translate,Search,Rerank,Generate,Critic,Answer,Trace white
    class Qdrant,LangFuse storage
```