from enum import Enum


class Slicer(Enum):
    ORCA = "orcaslicer"
    PRUSA = "prusaslicer"
    BAMBU = "bambustudio"

    @staticmethod
    def detect(gcode: list[str]) -> "Slicer":
        for line in gcode[:10]:
            if "PrusaSlicer" in line:
                return Slicer.PRUSA
            elif "OrcaSlicer" in line:
                return Slicer.ORCA
            elif "BambuStudio" in line:
                return Slicer.BAMBU
        raise ValueError("Slicer not detected")


class SlicerSyntax:
    slicer: Slicer = Slicer.ORCA

    line_type: str = ";TYPE:"
    line_type_top_surface: str = "Top surface"
    line_type_outer_wall: str = "Outer wall"
    line_type_inner_wall: str = "Inner wall"
    line_type_bridge: str = "Bridge"
    line_type_ironing: str = "Ironing"
    line_type_overhang: str = "Overhang wall"

    layer_change: str = ";LAYER_CHANGE"
    z: str = ";Z:"
    height: str = ";HEIGHT:"
    width: str = ";WIDTH:"

    wipe_start: str = ";WIPE_START"
    wipe_end: str = ";WIPE_END"

    config_block_start: str = "; CONFIG_BLOCK_START"
    config_block_end: str = "; CONFIG_BLOCK_END"

    executable_block_start: str = "; EXECUTABLE_BLOCK_START"
    executable_block_end: str = "; EXECUTABLE_BLOCK_END"

    def __init__(self, slicer: Slicer):
        self.slicer = slicer
        match slicer:
            case Slicer.PRUSA:
                self.line_type_bridge = "Bridge infill"
            case Slicer.BAMBU:
                self.layer_change = "; CHANGE_LAYER"
                self.line_type = "; FEATURE:"
                self.z = "; Z_HEIGHT:"
                self.height = "; LAYER_HEIGHT:"
                self.width = "; LINE_WIDTH:"
