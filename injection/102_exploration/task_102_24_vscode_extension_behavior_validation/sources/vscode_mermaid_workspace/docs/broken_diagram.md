# Broken Diagram Fixture

The selected extension should not silently report this malformed diagram as successful.

```mermaid
flowchart TD
  A[Start --> B{Missing bracket}
  B -->|yes| C[Done]
```
