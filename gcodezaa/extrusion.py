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
        extra_z = height * 0.75
        rays = [
            [
                self.p[0] + dx * i / num_segments,
                self.p[1] + dy * i / num_segments,
                z + extra_z,
                0,
                0,
                -1,
            ]
            for i in range(num_segments + 1)
        ]
        hits = scene.cast_rays(
            open3d.core.Tensor(rays, dtype=open3d.core.Dtype.Float32)
        )

        extrusion_rate = self.e / self.length()

        segments = []
        p = self.p
        for i, hit in enumerate(hits["t_hit"]):
            d = extra_z - hit.item()
            if hits["primitive_normals"][i][2].item() < 0:
                d = float("inf")
            # TODO: proper detection if the surface is covered by another line
            # in the next layer to avoid blobs
            # Percentage coverage would be even better as a transition factor
            # between normal z and contoured z.
            is_top = d <= (height / 2 + 1e-6) or ironing_line
            d = max(-height / 2, min(height / 2, d)) if is_top else 0

            do_split = demo_split is not None and rays[i][1] < demo_split

            segment = Extrusion(
                p=p,
                x=rays[i][0],
                y=rays[i][1],
                z=z if do_split else z + d,
                e=None,
                f=self.f,
                relative=False,
            )
            if segment.length() == 0:
                continue
            segment.meta = f"d={hit.item():.3g}"

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
