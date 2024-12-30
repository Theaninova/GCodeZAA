# GCodeZAA

This is a post-processing script to enable smooth(-ish) non-planar top surfaces through
a process I've come to call "Z Anti-Aliasing", to differentiate it from true non-planar
top surfaces.

This script is not super user friendly, but should be fine as a proof-of-concept to hopefully
get this implemented in slicers directly.

## Limitations

- Only works in OrcaSlicer
- Non-planar extrusion flow is not great and needs further testing
- Overlapping/double extrusion (this might be solveable by using ironing lines)
- Random artifacts in walls (this might be solveable by using ironing lines)
- Only STLs are supported
- Requres inner/outer wall order
- Only Klipper is supported (marlin could be done with some more work)

## Usage

1. Slice normally
2. Create a new directory for the plate models
3. For each object on the plate, right click and select "Export as one STL..." and save it **as the exact object name** to the directory

## Results

![](./images/benchy_roof_side.jpg)
![](./images/benchy_side.jpg)
