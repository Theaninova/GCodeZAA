from gcodezaa.context import ProcessorContext
from gcodezaa.extrusion import Extrusion
import os
import re
import open3d


def parse_simple_args(gcode: str) -> dict:
    return dict(map(lambda x: (x[0], x[1:].strip()), gcode.split(" ")))


def parse_klipper_args(gcode: str) -> dict:
    return dict(map(lambda x: list(map(str.strip, x.split("=", 1))), gcode.split(" ")))


def process_gcode(gcode: list[str], model_dir: str) -> list[str]:
    ctx = ProcessorContext(gcode, model_dir)
    is_in_executable = False
    while ctx.gcode_line < len(ctx.gcode):
        if not is_in_executable and ctx.line.startswith(
            ctx.syntax.executable_block_start
        ):
            is_in_executable = True
        elif is_in_executable and ctx.line.startswith(ctx.syntax.executable_block_end):
            break
        elif is_in_executable:
            process_line(ctx)
        ctx.gcode_line += 1

    return ctx.gcode


def process_line(ctx: ProcessorContext):
    write_back = ""
    ctx.extrusion = []

    if ctx.line.startswith("G0 ") or ctx.line.startswith("G1 "):
        args = parse_simple_args(ctx.line)
        ctx.extrusion.append(
            Extrusion(
                p=ctx.last_p,
                x=float(args["X"]) if "X" in args else None,
                y=float(args["Y"]) if "Y" in args else None,
                z=float(args["Z"]) if "Z" in args else None,
                e=float(args["E"]) if "E" in args else None,
                f=float(args["F"]) if "F" in args else None,
                relative=ctx.relative_positioning,
            )
        )
    elif ctx.line.startswith("G2 "):
        # TODO: cw arc move
        pass
    elif ctx.line.startswith("G3 "):
        # TODO: ccw arc move
        pass
    elif ctx.line.startswith(ctx.syntax.line_type):
        ctx.line_type = ctx.line.removeprefix(ctx.syntax.line_type).strip()
    elif ctx.line.startswith(ctx.syntax.layer_change):
        ctx.layer += 1
        ctx.line_type = ctx.syntax.line_type_inner_wall  # doesn't get emitted properly
    elif ctx.line.startswith(ctx.syntax.z):
        ctx.z = float(ctx.line.removeprefix(ctx.syntax.z))
    elif ctx.line.startswith(ctx.syntax.height):
        ctx.height = float(ctx.line.removeprefix(ctx.syntax.height))
    elif ctx.line.startswith(ctx.syntax.width):
        ctx.width = float(ctx.line.removeprefix(ctx.syntax.width))
    elif ctx.line.startswith(ctx.syntax.wipe_start):
        ctx.wipe = True
    elif ctx.line.startswith(ctx.syntax.wipe_end):
        ctx.wipe = False
    elif ctx.line.startswith("M82"):
        ctx.relative_extrusion = False
    elif ctx.line.startswith("M83"):
        ctx.relative_extrusion = True
    elif ctx.line.startswith("G90"):
        ctx.relative_positioning = False
    elif ctx.line.startswith("G91"):
        ctx.relative_positioning = True
    elif ctx.line.startswith("G92"):
        args = parse_simple_args(ctx.line)
        if "E" in args:
            ctx.last_e = float(args["E"])
        if "X" in args or "Y" in args or "Z" in args:
            ctx.last_p = (
                float(args.get("X", ctx.last_p[0])),
                float(args.get("Y", ctx.last_p[1])),
                float(args.get("Z", ctx.last_p[2])),
            )
        pass
    elif ctx.line.startswith("M73"):
        args = parse_simple_args(ctx.line)
        if "P" in args:
            ctx.progress_percent = float(args["P"])
        if "R" in args:
            ctx.progress_remaining_minutes = float(args["R"])
    elif ctx.line.startswith("EXCLUDE_OBJECT_DEFINE"):
        args = parse_klipper_args(ctx.line.removeprefix("EXCLUDE_OBJECT_DEFINE "))
        name = args["NAME"]
        x, y = map(float, args["CENTER"].split(","))
        model_path = os.path.join(
            ctx.model_dir, re.sub(r"\.stl_.*$", ".stl", name)
        )  # dumb hack
        mesh = open3d.t.io.read_triangle_mesh(model_path, enable_post_processing=True)
        min_bound = mesh.get_min_bound()
        max_bound = mesh.get_max_bound()
        center = min_bound + (max_bound - min_bound) / 2
        mesh.translate(
            [x - center[0].item(), y - center[1].item(), -min_bound[2].item()]
        )

        scene = open3d.t.geometry.RaycastingScene()
        scene.add_triangles(mesh)

        ctx.exclude_object[name] = scene
    elif ctx.line.startswith("EXCLUDE_OBJECT_START"):
        args = parse_klipper_args(ctx.line.removeprefix("EXCLUDE_OBJECT_START "))
        ctx.active_object = ctx.exclude_object[args["NAME"]]
    elif ctx.line.startswith("EXCLUDE_OBJECT_END"):
        ctx.active_object = None

    if (
        len(ctx.extrusion) == 1
        and not ctx.wipe
        and ctx.active_object is not None
        and (
            ctx.line_type == ctx.syntax.line_type_ironing
            or ctx.line_type == ctx.syntax.line_type_top_surface
            or ctx.line_type == ctx.syntax.line_type_outer_wall
            or ctx.line_type == ctx.syntax.line_type_inner_wall
        )
        and not ctx.relative_positioning
        and ctx.extrusion[0].length() != 0
        and ctx.extrusion[0].e is not None
        and (ctx.extrusion[0].x is not None or ctx.extrusion[0].y is not None)
    ):
        contour = ctx.extrusion[0].contour_z(
            ctx.active_object,
            z=ctx.z,
            height=ctx.height,
            ironing_line=ctx.line_type == ctx.syntax.line_type_ironing,
        )
        if any(map(lambda extrusion: extrusion.z != ctx.z, contour)):
            ctx.extrusion = contour
            write_back = f"{ctx.line_type.upper()}_CONTOUR"

    if not write_back and ctx.last_p[2] != ctx.z and len(ctx.extrusion) > 0:
        ctx.extrusion = [
            Extrusion(
                p=ctx.last_p,
                x=None,
                y=None,
                z=ctx.z,
                e=None,
                f=None,
                relative=False,
            ),
            *ctx.extrusion,
        ]
        write_back = "RESET_Z"

    if len(ctx.extrusion) > 0:
        if ctx.extrusion[-1].e is not None:
            if ctx.relative_extrusion:
                # TODO
                pass
            else:
                ctx.last_e = ctx.extrusion[-1].e
        ctx.last_p = ctx.extrusion[-1].pos()

    if write_back == "":
        return

    if ctx.extrusion:
        ctx.gcode[ctx.gcode_line] = (
            f";{write_back} "
            + ctx.line
            + str.join(
                "",
                map(
                    lambda extrusion: (
                        ctx.line.split(" ", 1)[0]
                        + str(extrusion)
                        + ";"
                        + extrusion.meta
                        + "\n"
                    ),
                    ctx.extrusion,
                ),
            )
            + f";{write_back}_END\n"
        )
