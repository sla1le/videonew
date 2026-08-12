#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SVG-визуализации для кадров ECHORATE.

Генерирует standalone SVG 936x640 без внешних зависимостей. Получившийся
файл кладётся в build/img и используется существующим типом кадра photo.

Примеры:
    python3 build/visuals.py radar data.json build/img/radar.svg
    python3 build/visuals.py line data.json build/img/evolution.svg
    python3 build/visuals.py --self-test

Типы: radar, line, bar, timeline, quadrant.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

W = 936
H = 640
PAPER = "#FFFFFF"
INK = "#101010"
MUTED = "#8A8A8A"
RULE = "#E4E4E4"
GREEN = "#1E9A57"
RED = "#D7263D"
GOLD = "#D4AF37"


def esc(value):
    return html.escape(str(value), quote=True)


def num(value, name="value"):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s должен быть числом" % name)
    if not math.isfinite(float(value)):
        raise ValueError("%s должен быть конечным числом" % name)
    return float(value)


def clamp(value, low, high):
    return max(low, min(high, value))


def text(x, y, value, size=24, weight=400, anchor="start", fill=INK, family="Arial"):
    return (
        '<text x="%.1f" y="%.1f" font-family="%s" font-size="%d" '
        'font-weight="%d" text-anchor="%s" fill="%s">%s</text>'
        % (x, y, family, size, weight, anchor, fill, esc(value))
    )


def line(x1, y1, x2, y2, stroke=RULE, width=2, dash=""):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    return (
        '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
        'stroke="%s" stroke-width="%s"%s/>'
        % (x1, y1, x2, y2, stroke, width, d)
    )


def circle(cx, cy, r, fill=INK, stroke="none", width=0):
    return (
        '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="%s"/>'
        % (cx, cy, r, fill, stroke, width)
    )


def poly(points, stroke=INK, width=5, fill="none", opacity=1.0):
    pts = " ".join("%.1f,%.1f" % (x, y) for x, y in points)
    return (
        '<polygon points="%s" fill="%s" fill-opacity="%.3f" stroke="%s" '
        'stroke-width="%s" stroke-linejoin="round"/>'
        % (pts, fill, opacity, stroke, width)
    )


def path(points, stroke=INK, width=5):
    if not points:
        return ""
    d = "M %.1f %.1f" % points[0]
    for x, y in points[1:]:
        d += " L %.1f %.1f" % (x, y)
    return '<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>' % (d, stroke, width)


def wrapper(body, title="ECHORATE visual"):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
        'role="img" aria-labelledby="echorate-title echorate-desc">'
        '<title id="echorate-title">%s</title>'
        '<desc id="echorate-desc">Визуализация данных ECHORATE</desc>'
        '<rect width="100%%" height="100%%" fill="%s"/>'
        '%s</svg>' % (W, H, W, H, esc(title), PAPER, body)
    )


def require_list(data, key, minimum=1, maximum=None):
    value = data.get(key)
    if not isinstance(value, list):
        raise ValueError("%s должен быть массивом" % key)
    if len(value) < minimum:
        raise ValueError("%s: минимум %d" % (key, minimum))
    if maximum is not None and len(value) > maximum:
        raise ValueError("%s: максимум %d" % (key, maximum))
    return value


def radar(data):
    axes = require_list(data, "axes", 3, 6)
    series = require_list(data, "series", 1, 2)
    low = num(data.get("min", 30), "min")
    high = num(data.get("max", 99), "max")
    if high <= low:
        raise ValueError("max должен быть больше min")

    cx, cy, radius = 468.0, 320.0, 212.0
    angles = [-math.pi / 2 + i * (2 * math.pi / len(axes)) for i in range(len(axes))]
    out = []

    for ring in (0.25, 0.5, 0.75, 1.0):
        pts = [(cx + math.cos(a) * radius * ring, cy + math.sin(a) * radius * ring) for a in angles]
        out.append(poly(pts, stroke=RULE, width=2, fill="none"))

    for angle, label in zip(angles, axes):
        ex = cx + math.cos(angle) * radius
        ey = cy + math.sin(angle) * radius
        out.append(line(cx, cy, ex, ey, RULE, 2))
        lx = cx + math.cos(angle) * (radius + 54)
        ly = cy + math.sin(angle) * (radius + 54) + 8
        anchor = "middle"
        if math.cos(angle) > 0.3:
            anchor = "start"
        elif math.cos(angle) < -0.3:
            anchor = "end"
        out.append(text(lx, ly, str(label).upper(), 20, 700, anchor, MUTED))

    colors = [INK, MUTED]
    fills = [INK, MUTED]
    for idx, item in enumerate(series):
        values = item.get("values")
        if not isinstance(values, list) or len(values) != len(axes):
            raise ValueError("series[%d].values должен совпадать с axes" % idx)
        pts = []
        for angle, raw in zip(angles, values):
            value = clamp(num(raw), low, high)
            ratio = (value - low) / (high - low)
            pts.append((cx + math.cos(angle) * radius * ratio, cy + math.sin(angle) * radius * ratio))
        out.append(poly(pts, stroke=colors[idx], width=5, fill=fills[idx], opacity=0.08 if idx == 0 else 0.035))
        for x, y in pts:
            out.append(circle(x, y, 5, colors[idx]))

    legend_x = 36
    for idx, item in enumerate(series):
        y = 598
        x = legend_x + idx * 330
        out.append(line(x, y - 7, x + 38, y - 7, colors[idx], 5))
        out.append(text(x + 52, y, item.get("name", "СЕРИЯ %d" % (idx + 1)), 22, 700, "start", colors[idx]))

    return wrapper("".join(out), data.get("title", "Radar ECHORATE"))


def line_chart(data):
    series = require_list(data, "series", 1, 4)
    low = num(data.get("min", 0), "min")
    high = num(data.get("max", 100), "max")
    if high <= low:
        raise ValueError("max должен быть больше min")

    all_points = [item.get("points") for item in series]
    if any(not isinstance(points, list) or len(points) < 2 for points in all_points):
        raise ValueError("каждая серия line требует минимум две точки")
    count = max(len(points) for points in all_points)
    if count > 12:
        raise ValueError("line: максимум 12 точек на серию")

    left, right, top, bottom = 76.0, 876.0, 60.0, 526.0
    out = []
    for i in range(5):
        y = top + (bottom - top) * i / 4.0
        value = high - (high - low) * i / 4.0
        out.append(line(left, y, right, y, RULE, 2))
        out.append(text(left - 18, y + 8, "%g" % value, 18, 400, "end", MUTED))

    colors = [INK, MUTED, GREEN, RED]
    for sidx, item in enumerate(series):
        points = item["points"]
        coords = []
        for i, point in enumerate(points):
            if not isinstance(point, dict):
                raise ValueError("line point должен быть объектом")
            value = clamp(num(point.get("value")), low, high)
            x = left + (right - left) * i / max(1, len(points) - 1)
            y = bottom - (value - low) / (high - low) * (bottom - top)
            coords.append((x, y))
        out.append(path(coords, colors[sidx], 5 if sidx == 0 else 4))
        for i, (x, y) in enumerate(coords):
            if i in (0, len(coords) - 1) or item["points"][i].get("label_value"):
                out.append(circle(x, y, 5, colors[sidx]))
                out.append(text(x, y - 16, "%g" % num(item["points"][i]["value"]), 18, 700, "middle", colors[sidx]))

    labels = series[0]["points"]
    for i, point in enumerate(labels):
        if i not in (0, len(labels) - 1) and not point.get("show_label"):
            continue
        x = left + (right - left) * i / max(1, len(labels) - 1)
        out.append(text(x, 566, point.get("label", i + 1), 18, 700, "middle", MUTED))

    for idx, item in enumerate(series):
        x = 76 + idx * 205
        out.append(line(x, 610, x + 28, 610, colors[idx], 5))
        out.append(text(x + 38, 617, item.get("name", "СЕРИЯ %d" % (idx + 1)), 18, 700, "start", colors[idx]))

    return wrapper("".join(out), data.get("title", "Line ECHORATE"))


def bar_chart(data):
    items = require_list(data, "items", 1, 8)
    low = num(data.get("min", 0), "min")
    max_value = max(num(item.get("value")) for item in items)
    high = num(data.get("max", max_value), "max")
    if high <= low:
        raise ValueError("max должен быть больше min")
    accent = data.get("accent")

    left, right, top, bottom = 170.0, 884.0, 54.0, 568.0
    row_h = (bottom - top) / len(items)
    out = []
    for idx, item in enumerate(items):
        value = clamp(num(item.get("value")), low, high)
        y = top + idx * row_h
        cy = y + row_h * 0.5
        out.append(text(left - 18, cy + 8, item.get("label", idx + 1), 22, 700, "end", INK))
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="20" fill="%s"/>' % (left, cy - 10, right - left, RULE))
        width = (value - low) / (high - low) * (right - left)
        color = GREEN if accent is not None and (accent == idx or accent == item.get("label")) else INK
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="20" fill="%s"/>' % (left, cy - 10, width, color))
        out.append(text(min(right, left + width + 14), cy + 8, "%g" % value, 22, 700, "start", color))
    return wrapper("".join(out), data.get("title", "Bar ECHORATE"))


def timeline(data):
    items = require_list(data, "items", 2, 8)
    left, right, y = 70.0, 866.0, 324.0
    out = [line(left, y, right, y, INK, 4)]
    for idx, item in enumerate(items):
        x = left + (right - left) * idx / max(1, len(items) - 1)
        up = idx % 2 == 0
        end_y = y - 116 if up else y + 116
        out.append(line(x, y, x, end_y, MUTED, 2))
        out.append(circle(x, y, 8, INK))
        out.append(text(x, end_y - 18 if up else end_y + 34, item.get("date", ""), 20, 700, "middle", MUTED))
        title_y = end_y + 14 if up else end_y + 68
        out.append(text(x, title_y, item.get("title", ""), 20, 700, "middle", INK))
    return wrapper("".join(out), data.get("title", "Timeline ECHORATE"))


def quadrant(data):
    points = require_list(data, "points", 1, 10)
    x_label = data.get("x_label", "X")
    y_label = data.get("y_label", "Y")
    left, right, top, bottom = 126.0, 852.0, 62.0, 546.0
    mid_x = (left + right) / 2.0
    mid_y = (top + bottom) / 2.0
    out = [
        line(left, bottom, right, bottom, INK, 3),
        line(left, top, left, bottom, INK, 3),
        line(mid_x, top, mid_x, bottom, RULE, 2, "8,8"),
        line(left, mid_y, right, mid_y, RULE, 2, "8,8"),
        text((left + right) / 2.0, 602, x_label, 22, 700, "middle", MUTED),
        text(42, (top + bottom) / 2.0, y_label, 22, 700, "middle", MUTED),
    ]
    for idx, item in enumerate(points):
        xv = clamp(num(item.get("x")), 0, 100)
        yv = clamp(num(item.get("y")), 0, 100)
        x = left + xv / 100.0 * (right - left)
        y = bottom - yv / 100.0 * (bottom - top)
        color = GREEN if item.get("accent") else INK
        out.append(circle(x, y, 8, color))
        anchor = "start" if x < right - 120 else "end"
        dx = 14 if anchor == "start" else -14
        out.append(text(x + dx, y - 12, item.get("label", idx + 1), 20, 700, anchor, color))
    return wrapper("".join(out), data.get("title", "Quadrant ECHORATE"))


RENDERERS = {
    "radar": radar,
    "line": line_chart,
    "bar": bar_chart,
    "timeline": timeline,
    "quadrant": quadrant,
}


def render(kind, data):
    if kind not in RENDERERS:
        raise ValueError("неизвестный тип %s" % kind)
    return RENDERERS[kind](data)


def self_test():
    samples = {
        "radar": {
            "axes": ["ТЕКСТЫ", "ЗВУК", "ПОДАЧА", "ХИТЫ", "ЛАЙВЫ", "ВЛИЯНИЕ"],
            "series": [{"name": "A", "values": [80, 90, 78, 88, 70, 84]}, {"name": "B", "values": [84, 82, 89, 76, 74, 80]}],
            "min": 30, "max": 99,
        },
        "line": {"min": 30, "max": 99, "series": [{"name": "OVR", "points": [{"label": "2023", "value": 81}, {"label": "2024", "value": 89}, {"label": "2025", "value": 86}]}]},
        "bar": {"items": [{"label": "A", "value": 191.9}, {"label": "B", "value": 132.8}], "accent": 0},
        "timeline": {"items": [{"date": "2023", "title": "СТАРТ"}, {"date": "2024", "title": "РОСТ"}, {"date": "2025", "title": "ПИК"}]},
        "quadrant": {"x_label": "ОХВАТ", "y_label": "ПОДПИСКА", "points": [{"label": "ДУЭЛЬ", "x": 90, "y": 55, "accent": True}, {"label": "РАЗБОР", "x": 45, "y": 90}]},
    }
    for kind, data in samples.items():
        svg = render(kind, data)
        root = ET.fromstring(svg)
        if not root.tag.endswith("svg"):
            raise AssertionError("%s: корень не svg" % kind)
        if 'viewBox="0 0 936 640"' not in svg:
            raise AssertionError("%s: неверный viewBox" % kind)
        print("  ok    %s" % kind)
    print("SVG-визуализации прошли самотест.")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", nargs="?", choices=sorted(RENDERERS))
    parser.add_argument("input", nargs="?")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.kind or not args.input or not args.output:
        parser.error("нужны TYPE input.json output.svg или --self-test")

    with open(args.input, encoding="utf-8") as handle:
        data = json.load(handle)
    svg = render(args.kind, data)
    parent = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(parent, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(svg)
    print("SVG собран: %s" % args.output)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, json.JSONDecodeError) as err:
        print("ПРОВАЛ: %s" % err)
        sys.exit(1)
