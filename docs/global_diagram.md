flowchart LR
 subgraph subGraph0["Faza Przetwarzania DSL"]
        Blueprint["Blueprint (YAML DSL)"]
        Repair["State Machine Repair (Sanityzacja YAML)"]
  end
 subgraph subGraph1["DSL Engine"]
        Graph["Analiza pliku DSL (Graph-based Relation Inference)"]
        Jinja["Generator Jinja2"]
        NestJS["Kod NestJS (Encje, Kontrolery, DTO)"]
  end
    Start(("Start: Opis Naturalny")) --> AI["Warstwa LLM (Multi-provider Fallback)"]
    AI --> Path{"Wybór ścieżki"}
    Path -- Tradycyjna (Direct) --> Fix["Zaawansowany Prompting i Sanityzacja"]
    Fix --> DirectLLM["Bezpośredni Wynik LLM"]
    DirectLLM --> DirectCode["Kod NestJS"]
    Path -- Proponowana (DSL) --> Repair
    Repair --> Blueprint
    Blueprint --> Graph
    Graph --> Jinja
    Jinja --> NestJS
    DirectCode --> Val["Walidacja (tsc, npm, python subprocess)"]
    NestJS --> Val
    Val -.-> Logs["Pipeline Logi (Metryki, Raporty błędów)"]
    Val -- Sukces --> Success(("Aplikacja Backendowa"))

     Blueprint:::logic
     Repair:::logic
     Graph:::logic
     Jinja:::logic
     NestJS:::logic
     Start:::input
     AI:::ai
     Fix:::error
     DirectLLM:::error
     DirectCode:::error
     Val:::check
     Logs:::logs
     Success:::input
    classDef input fill:#f5f5f5,stroke:#333,stroke-width:2px
    classDef ai fill:#f9f,stroke:#333,stroke-width:2px
    classDef logic fill:#d1e7ff,stroke:#004a99,stroke-width:2px
    classDef check fill:#d5e8d4,stroke:#82b366,stroke-width:2px
    classDef error fill:#fbb,stroke:#333,stroke-dasharray: 5 5
    classDef logs fill:#fff,stroke:#333,stroke-dasharray: 2 2