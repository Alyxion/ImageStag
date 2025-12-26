# Filter Graphs

Filter graphs enable complex processing with branching, merging, and multi-input/output filters.

## Graph Structure

A graph consists of:
- **Nodes**: Filters, sources, and outputs
- **Connections**: Directed edges between node ports

```python
from imagestag.filters import FilterGraph, GraphNode, GraphConnection
from imagestag.filters import GaussianBlur, Blend, PipelineSource, PipelineOutput

# Create graph
graph = FilterGraph()

# Add source node
graph.add_node(GraphNode(
    name='source',
    source=PipelineSource(input_type='IMAGE')
))

# Add filter nodes
graph.add_node(GraphNode(name='blur', filter=GaussianBlur(radius=5)))
graph.add_node(GraphNode(name='blend', filter=Blend(opacity=0.5)))

# Add output node
graph.add_node(GraphNode(
    name='output',
    output_spec=PipelineOutput(output_type='IMAGE'),
    is_output=True
))

# Connect nodes
graph.add_connection(GraphConnection(from_node='source', to_node='blur'))
graph.add_connection(GraphConnection(from_node='source', to_node='blend', to_port='a'))
graph.add_connection(GraphConnection(from_node='blur', to_node='blend', to_port='b'))
graph.add_connection(GraphConnection(from_node='blend', to_node='output'))
```

## Executing Graphs

```python
# Single input
result = graph.execute(image)

# Multiple inputs
result = graph.execute(source_a=img1, source_b=img2)

# Designer mode (uses placeholder images)
result = graph.execute_designer()
```

## Multi-Input Filters

Filters with multiple inputs use named ports:

```python
from imagestag.filters import Blend, SizeMatcher

# Blend has ports: a, b, mask (optional)
blend_result = Blend(mode='multiply').apply_multi({
    'a': base_image,
    'b': overlay_image,
    'mask': alpha_mask  # optional
})

# SizeMatcher has ports: a, b
# Returns dict with outputs 'a' and 'b'
matched = SizeMatcher(mode='smaller').apply_multi({
    'a': image1,
    'b': image2
})
resized_a = matched['a']
resized_b = matched['b']
```

## Multi-Output Filters

Some filters produce multiple outputs:

```python
from imagestag.filters import SizeMatcher, SplitChannels

# SizeMatcher outputs both resized images
outputs = SizeMatcher(mode='smaller').apply_multi({'a': img1, 'b': img2})
# outputs = {'a': resized_img1, 'b': resized_img2}

# In graph, connect to specific output ports
graph.add_connection(GraphConnection(
    from_node='size_match',
    from_port='a',
    to_node='process_a'
))
```

## Geometry Filters

Detection filters output `GeometryList` instead of images:

```python
from imagestag.filters import FaceDetector, DrawGeometry

# Detect returns GeometryList
faces = FaceDetector().apply(image)

# Use with DrawGeometry
annotated = DrawGeometry(color='#FF0000').apply_multi({
    'input': image,
    'geometry': faces
})
```

## JSON Serialization

```python
# To JSON
graph_dict = graph.to_dict()
json_str = graph.to_json()

# From JSON
restored = FilterGraph.from_dict(graph_dict)
restored = FilterGraph.from_json(json_str)
```

### JSON Format

```json
{
  "nodes": {
    "source": {
      "class": "PipelineSource",
      "type": "IMAGE",
      "formats": ["RGB8", "RGBA8"]
    },
    "blur": {
      "class": "GaussianBlur",
      "params": {"radius": 5.0}
    },
    "output": {
      "class": "PipelineOutput",
      "type": "IMAGE",
      "name": "output"
    }
  },
  "connections": [
    {"from": "source", "to": "blur"},
    {"from": "blur", "to": "output"}
  ]
}
```

### Connection Formats

```json
// Simple: default ports (output -> input)
{"from": "source", "to": "blur"}

// Named to_port
{"from": "source", "to": ["blend", "a"]}

// Named both ports
{"from": ["size_match", "a"], "to": ["blend", "a"]}
```

## Port Naming Conventions

### Source Nodes
| Scenario | Names |
|----------|-------|
| Single input | `source` |
| Dual inputs | `source_a`, `source_b` |

### Input Ports
| Scenario | Ports |
|----------|-------|
| Single image | `input` |
| Dual images | `a`, `b` |
| Image + geometry | `input`, `geometry` |
| Image + mask | `input`, `mask` |

### Output Ports
| Scenario | Ports |
|----------|-------|
| Single output | `output` |
| Dual outputs | `a`, `b` |

## Example: Face Detection Graph

```python
from imagestag.filters import (
    FilterGraph, GraphNode, GraphConnection,
    PipelineSource, PipelineOutput,
    FaceDetector, DrawGeometry
)

graph = FilterGraph()

# Source
graph.add_node(GraphNode(
    name='source',
    source=PipelineSource(input_type='IMAGE')
))

# Face detection
graph.add_node(GraphNode(
    name='detect',
    filter=FaceDetector(scale_factor=1.3)
))

# Draw boxes
graph.add_node(GraphNode(
    name='draw',
    filter=DrawGeometry(color='#FF0000', thickness=2)
))

# Output
graph.add_node(GraphNode(
    name='output',
    output_spec=PipelineOutput(output_type='IMAGE'),
    is_output=True
))

# Connections
graph.connections = [
    GraphConnection(from_node='source', to_node='detect'),
    GraphConnection(from_node='source', to_node='draw', to_port='input'),
    GraphConnection(from_node='detect', to_node='draw', to_port='geometry'),
    GraphConnection(from_node='draw', to_node='output'),
]

# Execute
result = graph.execute(image)
```
