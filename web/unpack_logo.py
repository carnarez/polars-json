"""Add an unpacking animation to the `Polars` b(e)ar logo."""

import re
import sys
import xml.etree.ElementTree

# define the parameters for the animation; we expect three states, with two (start and
# end) to be repeated to take a break there
ANIMATION = {
    "calcMode": "spline",
    "dur": "10s",
    "keySplines": ";".join(["0.1 0.8 0.2 1" for _ in range(4)]),
    "keyTimes": "0;0.25;0.5;0.75;1",
    "repeatCount": "indefinite",
}

# define the style of the contour; think css, but not totally
CONTOUR_STYLE: str = ";".join(
    [
        f"{k}:{v}"
        for k, v in {
            "fill": "none",
            "stroke": "#539bf5",
            "stroke-opacity": 1,
            "stroke-width": 0.5,
        }.items()
    ],
)


def rect_coordinates(
    rect: list[xml.etree.ElementTree.Element],
) -> list[tuple[float, float]]:
    """Fetch the coordinates of all `rect` objects.

    Parameters
    ----------
    rect : list[xml.etree.ElementTree.Element]
        List of `Element` objects present in the SVG.

    Returns
    -------
    : list[tuple[float, float]]
        List of (x, y) pairs.

    """
    return [(float(r.get("x")), float(r.get("y"))) for r in rect]


def rect_dimensions(
    rect: list[xml.etree.ElementTree.Element],
) -> list[tuple[float, float]]:
    """Fetch the dimensions of all `rect` objects.

    Parameters
    ----------
    rect : list[xml.etree.ElementTree.Element]
        List of `Element` objects present in the SVG.

    Returns
    -------
    : list[tuple[float, float]]
        List of (width, height) pairs.

    """
    return [(float(r.get("width")), float(r.get("height"))) for r in rect]


def calculate_average_gap(rect: list[xml.etree.ElementTree.Element]) -> float:
    """Calculate an average for the gap between `rect` objects.

    Parameters
    ----------
    rect : list[xml.etree.ElementTree.Element]
        List of `Element` objects present in the SVG.

    Returns
    -------
    : float
        Averaged gap size between `rect` objects, as inferred from the bear.

    """
    crds: list[tuple[float, float]] = rect_coordinates(rect)
    dims: list[tuple[float, float]] = rect_dimensions(rect)

    gaps: list[float] = []

    # find the gaps
    x0 = 0
    for i, ((x, _y), (w, _h)) in enumerate(zip(crds, dims, strict=True)):
        if i and (g := x - x0) > 1e-3:
            gaps.append(g)

        # eww but am lazy today
        x0 = x + w

    return sum(gaps) / len(gaps)


def calculate_figure_center(
    rect: list[xml.etree.ElementTree.Element],
) -> tuple[float, float]:
    """Calculate the center of the figure.

    Parameters
    ----------
    rect : list[xml.etree.ElementTree.Element]
        List of `Element` objects present in the SVG.

    Returns
    -------
    : tuple[float, float]
        Coordinates (x, y) of the center.

    Notes
    -----
    We should not need to use the y component of the center down here.

    """
    crds: list[tuple[float, float]] = rect_coordinates(rect)

    return (
        sum([x for x, y in crds]) / len(crds),
        sum([y for x, y in crds]) / len(crds),
    )


def calculate_unpacked_width(rect: list[xml.etree.ElementTree.Element]) -> float:
    """Calculate the maximum width when unpacking the bear.

    Parameters
    ----------
    rect : list[xml.etree.ElementTree.Element]
        List of `Element` objects present in the SVG.

    Returns
    -------
    : float
        Total width of the SVG after unpacking the bear.

    """
    dims: list[tuple[float, float]] = rect_dimensions(rect)

    return sum([w for w, h in dims]) + calculate_average_gap(rect) * (len(rect) - 1)


def animate_svg(
    tree: xml.etree.ElementTree.ElementTree,
) -> xml.etree.ElementTree.ElementTree:
    """Update the dimensions of the SVG object and add the animation.

    Parameters
    ----------
    tree : list[xml.etree.ElementTree.ElementTree]
        The XML tree parsed from the SVG definition.

    Returns
    -------
    : list[xml.etree.ElementTree.ElementTree]
        Updated tree.

    """
    root: xml.etree.ElementTree.Element = tree.getroot()
    rect: list[xml.etree.ElementTree.Element] = list(root)

    # svg dimensions
    svg_width = calculate_unpacked_width(rect)
    svg_height = float("".join(re.findall(r"[\d\.]+", root.get("height"))))

    # centers of packed and unpacked figures
    bear_center = calculate_figure_center(rect)
    bars_center = (svg_width / 2, svg_height / 2)
    translation = bars_center[0] - bear_center[0]

    # gap between bars
    gap_size = calculate_average_gap(rect)

    # update svg properties
    root.set("width", f"{svg_width:.3f}mm")
    root.set("height", f"{svg_height:.3f}mm")
    root.set("viewBox", f"0 0 {svg_width:.3f} {svg_height:.3f}")

    # update rect properties
    x0 = 0
    for _i, r in enumerate(rect):
        # start -> end coordinates
        xs = float(r.get("x")) + translation
        ys = float(r.get("y"))
        xe = x0
        ye = svg_height / 2 - float(r.get("height")) / 2

        # add the animation; we add steps on purpose to stay at the position for a
        # little longer
        ANIMATION.update({"attributeName": "x", "values": f"{xs};{xe};{xe};{xs};{xs}"})
        r.append(xml.etree.ElementTree.Element("animate", ANIMATION))

        ANIMATION.update({"attributeName": "y", "values": f"{ys};{ye};{ye};{ys};{ys}"})
        r.append(xml.etree.ElementTree.Element("animate", ANIMATION))

        # initial properties
        r.set("style", CONTOUR_STYLE)
        r.set("x", str(xs))
        r.set("y", str(ys))

        # eww but am lazy today
        x0 += float(r.get("width")) + gap_size

    return tree


if __name__ == "__main__":
    tree = animate_svg(xml.etree.ElementTree.parse(sys.argv[1]))
    # remove namespaces that break the animation
    sys.stdout.write(
        xml.etree.ElementTree.tostring(tree.getroot(), encoding="utf-8")
        .decode()
        .replace(":ns0", "")
        .replace("ns0:", "")
        .replace("\n", ""),
    )
