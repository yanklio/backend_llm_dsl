
flowchart TD
    Start[Kod Projektu] --> TSC[1. Kompilacja: tsc]
    TSC -- OK --> Build[2. Build & Run]
    Build -- OK --> Endpoints[3. Test Endpointów]
    Endpoints -- OK --> Success((Aplikacja Działa))
    
    TSC -- Błąd --> Fail((Logi Błędów))
    Build -- Błąd --> Fail
    Endpoints -- Błąd --> Fail