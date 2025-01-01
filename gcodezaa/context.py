from gcodezaa.slicer_syntax import SlicerSyntax, Slicer
from gcodezaa.extrusion import Extrusion
import open3d


class ProcessorContext:
    syntax: SlicerSyntax
    config_block: dict[str, str] = {}
    model_dir: str
    gcode: list[str]
    gcode_line = 0

    line_type: str = ""

    last_p: tuple[float, float, float] = (0, 0, 0)
    last_e: float = 0
    last_contoured_z: float | None = None

    exclude_object: dict[str, open3d.t.geometry.RaycastingScene] = {}
    active_object: open3d.t.geometry.RaycastingScene | None = None

    extrusion: list[Extrusion] = []

    layer = 0
    z: float = 0
    height: float = 0
    width: float = 0
    wipe: bool = False

    relative_extrusion: bool = False
    relative_positioning: bool = False

    progress_percent: float = 0
    progress_remaining_minutes: float = 0

    def __init__(self, gcode: list[str], model_dir: str):
        self.gcode = gcode
        self.model_dir = model_dir
        self.syntax = SlicerSyntax(Slicer.detect(self.gcode))

        is_in_config = False
        for l in gcode:
            if not is_in_config and l.startswith(self.syntax.config_block_start):
                is_in_config = True
            elif is_in_config and l.startswith(self.syntax.config_block_end):
                break
            elif is_in_config:
                key, value = l.removeprefix(";").split("=", maxsplit=1)
                self.config_block[key.strip()] = value.strip()

    @property
    def line(self):
        return self.gcode[self.gcode_line]
