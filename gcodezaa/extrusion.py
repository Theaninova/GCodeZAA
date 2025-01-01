import math
import open3d


def format_gcode_number(number: float) -> str:
    formatted = f"{number:.6f}"
    formatted = formatted.rstrip("0")
    formatted = formatted.lstrip("0")
    return formatted


class Extrusion:
    p: tuple[float, float, float]
    x: float | None
    y: float | None
    z: float | None
    e: float | None
    f: float | None
    relative: bool
    meta = ""

    def __init__(
        self,
        p: tuple[float, float, float],
        x: float | None,
        y: float | None,
        z: float | None,
        e: float | None,
        f: float | None,
        relative: bool,
    ):
        self.p = p
        self.x = x
        self.y = y
        self.z = z
        self.e = e
        self.f = f
        self.relative = relative

    def __str__(self) -> str:
        line = ""
        if self.x is not None:
            line += f" X{format_gcode_number(self.x)}"
        if self.y is not None:
            line += f" Y{format_gcode_number(self.y)}"
        if self.z is not None:
            line += f" Z{format_gcode_number(self.z)}"
        if self.e is not None:
            line += f" E{format_gcode_number(self.e)}"
        if self.f is not None:
            line += f" F{format_gcode_number(self.f)}"
        return line

    def pos(self) -> tuple[float, float, float]:
        return (
            (
                self.p[0] + (self.x or 0),
                self.p[1] + (self.y or 0),
                self.p[2] + (self.z or 0),
            )
            if self.relative
            else (self.x or self.p[0], self.y or self.p[1], self.z or self.p[2])
        )

    def delta(self) -> tuple[float, float, float]:
        return (
            (self.x or 0, self.y or 0, self.z or 0)
            if self.relative
            else (
                self.x - self.p[0] if self.x is not None else 0,
                self.y - self.p[1] if self.y is not None else 0,
                self.z - self.p[2] if self.z is not None else 0,
            )
        )

    def length(self) -> float:
        delta = self.delta()
        return math.sqrt(delta[0] ** 2 + delta[1] ** 2 + delta[2] ** 2)

    def contour_z(
        self,
        scene: open3d.t.geometry.RaycastingScene,
        z: float,
        height: float,
        ironing_line: bool,
        outer_line: bool,
        resolution=0.1,
        demo_split: float | None = None,
    ) -> list["Extrusion"]:
        if self.relative:
            raise ValueError("Cannot contour with relative positioning")
        if not self.e:
            raise ValueError("Cannot contour with no extrusion")

        dx, dy, _ = self.delta()

        self.p = (self.p[0], self.p[1], z)

        num_segments = math.ceil(self.length() / resolution)
        rays_up = [
            [
                self.p[0] + dx * i / num_segments,
                self.p[1] + dy * i / num_segments,
                z,
                0,
                0,
                1,
            ]
            for i in range(num_segments + 1)
        ]
        hits_up = scene.cast_rays(
            open3d.core.Tensor(rays_up, dtype=open3d.core.Dtype.Float32)
        )
        rays_down = [
            [
                self.p[0] + dx * i / num_segments,
                self.p[1] + dy * i / num_segments,
                z,
                0,
                0,
                -1,
            ]
            for i in range(num_segments + 1)
        ]
        hits_down = scene.cast_rays(
            open3d.core.Tensor(rays_down, dtype=open3d.core.Dtype.Float32)
        )

        extrusion_rate = self.e / self.length()

        segments = []
        p = self.p
        for i in range(num_segments + 1):
            hit_up = max(0, abs(hits_up["t_hit"][i].item()))
            hit_down = max(0, abs(hits_down["t_hit"][i].item()))
            normal_up = hits_up["primitive_normals"][i]
            normal_down = hits_down["primitive_normals"][i]
            line_width = 0.4
            use_up = (
                (normal_up[2].item() > 0 and normal_up[2].item() <= 0)
                or normal_down[2].item() <= 0
                or hit_up <= hit_down
            )

            if use_up and hit_up <= height / 2:
                normal = normal_up
                coverage = math.tan(math.acos(normal[2].item())) * line_width / 4
                hit = max(0, min(height / 2, hit_up))
                if normal[2].item() < 0.5:
                    d = 0
                elif coverage > 0:
                    d = hit * max(
                        0, min(1, (1 - max(0, hit_up - height / 2) / coverage))
                    )
                else:
                    d = hit
            elif normal_down[2].item() > 0 and hit_down <= height / 2 + 1e-6:
                normal = normal_down
                d = max(-height / 2, -hit_down)
            else:
                d = 0

            do_split = demo_split is not None and rays_up[i][1] < demo_split

            segment = Extrusion(
                p=p,
                x=rays_up[i][0],
                y=rays_up[i][1],
                z=z if do_split else z + d,
                e=None,
                f=self.f,
                relative=False,
            )
            if segment.length() == 0:
                continue
            segment.meta = f"d={d:.3g}"

            if i != 0:
                extrusion_height = height + d
                segment.meta = f"e={extrusion_height:.3g} {segment.meta}"
                segment.e = (
                    extrusion_rate * segment.length()
                    if ironing_line or do_split
                    else (
                        extrusion_rate * segment.length() * (extrusion_height / height)
                    )
                )
                segment.e = segment.e if segment.e > 0 else 0

            if (
                len(segments) > 1
                and segments[-2].z == segment.z
                and segments[-1].z == segment.z
                and segments[-2].e is not None
                and segments[-1].e is not None
                and segment.e is not None
            ):
                segment.e += segments[-1].e
                segment.meta = segments[-1].meta + " " + segment.meta
                segments[-1] = segment
            else:
                segments.append(segment)
            p = segment.pos()

        return segments
