# DSL Reference

ImageStag provides a compact Domain-Specific Language for defining filters, pipelines, and graphs.

## Basic Syntax

```
filter arg1 arg2 key=value; filter2 arg
```

- **Space** separates arguments
- **`;`** separates statements (filters)
- **`=`** for keyword arguments
- **`#`** prefix for hex colors

## Filter Parsing

```python
from imagestag.filters import Filter

# Positional argument (primary parameter)
blur = Filter.parse("blur 2.0")
# Equivalent to: GaussianBlur(radius=2.0)

# Keyword arguments
resize = Filter.parse("resize scale=0.5")
# Equivalent to: Resize(scale=0.5)

# Multiple arguments
resize = Filter.parse("resize size=800,600")
# Equivalent to: Resize(size=(800, 600))

# Color values
draw = Filter.parse("drawgeometry color=#ff0000 thickness=2")
```

## Pipeline Parsing

```python
from imagestag.filters import FilterPipeline

# Semicolon-separated
pipeline = FilterPipeline.parse("blur 2.0; brightness 1.2")

# Pipe-separated
pipeline = FilterPipeline.parse("resize 0.5|blur 2.0|brightness 1.2")

# Mixed styles
pipeline = FilterPipeline.parse("resize scale=0.5; lens k1=-0.15 k2=0.02")
```

## Graph DSL

For complex graphs with branching and multi-I/O filters:

### Named Nodes

Define reusable nodes with `[name: filter args]`:

```
[nodename: filter arg1 arg2 key=value]
```

### Node References

Reference nodes in subsequent statements:

```
[f: facedetector]; drawgeometry input=source geometry=f
```

- **`source`** - Implicit first input
- **`source_a`**, **`source_b`** - Dual inputs
- **`nodename`** - Reference node's default output
- **`nodename.port`** - Reference specific port

### Port Assignments

Assign node outputs to filter input ports:

```
drawgeometry input=source geometry=f
blend a=m.a b=m.b mask=g
```

## Complete Examples

### Simple Pipeline

```
resize 0.5; blur 2.0; brightness 1.2
```

Equivalent to:
```python
FilterPipeline([
    Resize(scale=0.5),
    GaussianBlur(radius=2.0),
    Brightness(factor=1.2),
])
```

### Face Detection

```
[f: facedetector scale_factor=1.52 min_neighbors=3]; drawgeometry input=source geometry=f color=#ff0000 thickness=2
```

Equivalent graph:
```
source -> facedetector -> geometry
source -> drawgeometry.input
facedetector -> drawgeometry.geometry
drawgeometry -> output
```

### Size Matching with Blend

```
[m: size_match a=source_a b=source_b smaller]; [g: imgen linear #000 #fff format=gray]; blend a=m.a b=m.b mask=g
```

This creates:
1. `m`: SizeMatcher matching two inputs to smaller dimensions
2. `g`: Linear gradient (black to white, grayscale)
3. Blend using matched images and gradient as mask

### Lens Correction with Enhancement

```
lens k1=-0.2 k2=0.05; autocontrast; sharpen 1.2
```

## Parsing Graphs

```python
from imagestag.filters import FilterGraph

# Parse DSL to graph
graph = FilterGraph.parse_dsl("""
[f: facedetector scale_factor=1.3];
drawgeometry input=source geometry=f color=#00ff00
""")

# Execute
result = graph.execute(image)
```

## Filter Aliases

Common shorthand names:

| Alias | Filter |
|-------|--------|
| `blur`, `gaussian` | GaussianBlur |
| `gray`, `grey` | Grayscale |
| `lens` | LensDistortion |
| `imgen` | ImageGenerator |
| `size_match`, `sizematch` | SizeMatcher |
| `draw` | DrawGeometry |
| `extract` | ExtractRegions |
| `merge` | MergeRegions |
| `face`, `faces` | FaceDetector |
| `circles` | HoughCircleDetector |
| `lines` | HoughLineDetector |
| `rot90`, `rot180`, `rot270` | Rotate with angle |
| `rotcw`, `rotccw` | Rotate 90 clockwise/counter-clockwise |
| `mirror`, `fliplr` | Flip horizontal |
| `flipud`, `flipv` | Flip vertical |
| `lava` | FalseColor(colormap='hot') |
| `thermal` | FalseColor(colormap='inferno') |
| `plasma` | FalseColor(colormap='plasma') |
| `viridis` | FalseColor(colormap='viridis') |

## Type Inference

The parser infers types from values:

| Input | Inferred Type |
|-------|---------------|
| `2.0` | float |
| `42` | int |
| `true`, `false` | bool |
| `800,600` | tuple |
| `#ff0000` | Color (hex) |
| `red`, `blue` | Color (name) |
| `"text"` | string |
| `nodename` | node reference |
| `nodename.port` | port reference |
