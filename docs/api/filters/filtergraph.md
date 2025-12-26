# FilterGraph

Directed acyclic graph of filter operations.

A FilterGraph represents a complete image processing pipeline that can:
- Define input constraints via the source specification
- Have multiple named branches of sequential filters (legacy)
- Or use a node-based graph with arbitrary connections (new)
- Combine branch outputs using a CombinerFilter
- Be serialized to/from JSON for storage and sharing

Two storage modes:
- Branch mode: Simple sequential branches with optional combiner
- Node mode: Arbitrary DAG with named nodes and explicit connections

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `branches` | str | {} |  |
| `output` | any | None |  |
| `source` | any | None |  |
| `nodes` | str | {} |  |
| `connections` | list | [] |  |
| `layout` | str | None |  |
