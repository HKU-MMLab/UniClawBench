"""PPTX layout / quality probing — supervisor-side aid for slide tasks.

Renders a low-fidelity ASCII-like preview of each slide (text-box
outlines, picture rectangles, warning callouts) plus a JSON probe of
overflow / font-size / density warnings, so the supervisor can judge
slide readability without a full PowerPoint renderer in the loop.

Extracted from ``lib/runner/artifacts.py`` to keep that module focused
on the attempt-collection entry points; PPTX probing has its own
optional Pillow dependency and a distinct call site
(``_generate_pptx_quality_artifacts`` invoked from
``collect_attempt_artifacts``).
"""
from __future__ import annotations

import json
import re
import shutil
import textwrap
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from ..proxy import write_local


PPTX_QUALITY_DIR = "_pptx_quality"
PPTX_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def _slide_sort_key(name: str) -> tuple[int, str]:
    match = re.search(r"slide(\d+)\.xml$", name)
    return (int(match.group(1)) if match else 10**9, name)


def _emu_to_inches(value: str | None) -> float:
    try:
        return int(value or "0") / 914400.0
    except ValueError:
        return 0.0


def _box_from_xfrm(xfrm: ET.Element | None) -> dict[str, float]:
    if xfrm is None:
        return {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}
    off = xfrm.find("a:off", PPTX_NS)
    ext = xfrm.find("a:ext", PPTX_NS)
    return {
        "x": _emu_to_inches(off.get("x") if off is not None else None),
        "y": _emu_to_inches(off.get("y") if off is not None else None),
        "w": _emu_to_inches(ext.get("cx") if ext is not None else None),
        "h": _emu_to_inches(ext.get("cy") if ext is not None else None),
    }


def _text_from_shape(shape: ET.Element) -> str:
    raw = "".join(node.text or "" for node in shape.findall(".//a:t", PPTX_NS))
    return " ".join(raw.split())


def _font_sizes_from_shape(shape: ET.Element) -> list[float]:
    sizes: list[float] = []
    for node in shape.findall(".//a:rPr", PPTX_NS) + shape.findall(".//a:defRPr", PPTX_NS):
        value = node.get("sz")
        if not value:
            continue
        try:
            sizes.append(int(value) / 100.0)
        except ValueError:
            continue
    return sizes


def _estimate_text_capacity(chars_box: dict[str, float], font_size: float) -> int:
    width = max(chars_box.get("w", 0.0), 0.05)
    height = max(chars_box.get("h", 0.0), 0.05)
    size = max(font_size, 8.0)
    char_width_in = size * 0.52 / 72.0
    line_height_in = size * 1.20 / 72.0
    chars_per_line = max(1, int(width / max(char_width_in, 0.01)))
    lines = max(1, int(height / max(line_height_in, 0.01)))
    return chars_per_line * lines


def _overlap_ratio(a: dict[str, float], b: dict[str, float]) -> float:
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    iw = max(0.0, min(ax2, bx2) - max(a["x"], b["x"]))
    ih = max(0.0, min(ay2, by2) - max(a["y"], b["y"]))
    inter = iw * ih
    smaller = max(min(a["w"] * a["h"], b["w"] * b["h"]), 0.01)
    return inter / smaller


def _probe_pptx_layout(path: Path) -> dict[str, Any]:
    probe: dict[str, Any] = {
        "file": path.name,
        "ok": False,
        "slide_count": 0,
        "slide_size_inches": {"w": 13.333, "h": 7.5},
        "warnings": [],
        "slides": [],
    }
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "ppt/presentation.xml" in names:
                pres = ET.fromstring(archive.read("ppt/presentation.xml"))
                size = pres.find("p:sldSz", PPTX_NS)
                if size is not None:
                    probe["slide_size_inches"] = {
                        "w": _emu_to_inches(size.get("cx")) or 13.333,
                        "h": _emu_to_inches(size.get("cy")) or 7.5,
                    }
            slide_names = sorted(
                [name for name in names if re.match(r"ppt/slides/slide\d+\.xml$", name)],
                key=_slide_sort_key,
            )
            probe["slide_count"] = len(slide_names)
            for index, slide_name in enumerate(slide_names, start=1):
                root = ET.fromstring(archive.read(slide_name))
                slide: dict[str, Any] = {
                    "index": index,
                    "text_chars": 0,
                    "text_boxes": [],
                    "picture_count": 0,
                    "warnings": [],
                }
                for shape in root.findall(".//p:sp", PPTX_NS):
                    text = _text_from_shape(shape)
                    if not text:
                        continue
                    box = _box_from_xfrm(shape.find("./p:spPr/a:xfrm", PPTX_NS))
                    sizes = _font_sizes_from_shape(shape)
                    min_font = min(sizes) if sizes else 18.0
                    capacity = _estimate_text_capacity(box, min_font)
                    density = len(text) / max(box["w"] * box["h"], 0.05)
                    overflow_ratio = len(text) / max(capacity, 1)
                    entry = {
                        "chars": len(text),
                        "preview": text[:160],
                        "box": box,
                        "min_font_pt": round(min_font, 1),
                        "estimated_capacity_chars": capacity,
                        "estimated_overflow_ratio": round(overflow_ratio, 2),
                        "density_chars_per_in2": round(density, 1),
                    }
                    if overflow_ratio > 1.20:
                        slide["warnings"].append(
                            f"text box may overflow: {len(text)} chars vs estimated capacity {capacity}"
                        )
                    if min_font < 9 and len(text) > 40:
                        slide["warnings"].append(f"very small text detected: {min_font:.1f} pt")
                    if density > 230 and len(text) > 120:
                        slide["warnings"].append(f"high text density detected: {density:.0f} chars/in^2")
                    slide["text_chars"] += len(text)
                    slide["text_boxes"].append(entry)
                for pic in root.findall(".//p:pic", PPTX_NS):
                    box = _box_from_xfrm(pic.find("./p:spPr/a:xfrm", PPTX_NS))
                    slide.setdefault("pictures", []).append({"box": box})
                    slide["picture_count"] += 1
                boxes = [box["box"] for box in slide["text_boxes"] if box["box"]["w"] and box["box"]["h"]]
                for left_index, left in enumerate(boxes):
                    for right in boxes[left_index + 1 :]:
                        if _overlap_ratio(left, right) > 0.18:
                            slide["warnings"].append("text boxes appear to overlap materially")
                            break
                    if "text boxes appear to overlap materially" in slide["warnings"]:
                        break
                if slide["text_chars"] > 1500:
                    slide["warnings"].append("slide has very high total text volume")
                probe["slides"].append(slide)
            probe["ok"] = True
    except Exception as exc:
        probe["warnings"].append(f"pptx probe failed: {exc}")
    warning_count = sum(len(slide.get("warnings", [])) for slide in probe.get("slides", [])) + len(probe["warnings"])
    dense_slides = sum(1 for slide in probe.get("slides", []) if slide.get("text_chars", 0) > 900)
    probe["summary"] = {
        "warning_count": warning_count,
        "dense_slide_count": dense_slides,
        "slides_with_warnings": [
            slide["index"] for slide in probe.get("slides", []) if slide.get("warnings")
        ],
        "requires_human_visual_review": True,
    }
    return probe


def _write_pptx_preview_images(probe: dict[str, Any], out_dir: Path) -> list[str]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return []

    def safe_draw_text(draw: Any, xy: tuple[int, int], text: str, *, fill: str) -> None:
        safe = str(text).encode("latin-1", errors="replace").decode("latin-1")
        draw.text(xy, safe, fill=fill, font=font)

    slide_w = float(probe.get("slide_size_inches", {}).get("w") or 13.333)
    slide_h = float(probe.get("slide_size_inches", {}).get("h") or 7.5)
    width_px = 1600
    height_px = max(1, int(width_px * slide_h / max(slide_w, 0.01)))
    sx = width_px / max(slide_w, 0.01)
    sy = height_px / max(slide_h, 0.01)
    font = ImageFont.load_default()
    written: list[str] = []
    for slide in probe.get("slides", [])[:24]:
        image = Image.new("RGB", (width_px, height_px), "#f7f7f2")
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, width_px - 1, height_px - 1], outline="#b7b7ae", width=3)
        safe_draw_text(draw, (16, 12), f"Slide {slide['index']} layout preview", fill="#111111")
        for pic in slide.get("pictures", []):
            box = pic.get("box", {})
            rect = [
                int(box.get("x", 0) * sx),
                int(box.get("y", 0) * sy),
                int((box.get("x", 0) + box.get("w", 0)) * sx),
                int((box.get("y", 0) + box.get("h", 0)) * sy),
            ]
            draw.rectangle(rect, outline="#3973c2", width=4)
            safe_draw_text(draw, (rect[0] + 6, rect[1] + 6), "figure/image", fill="#3973c2")
        for text_box in slide.get("text_boxes", []):
            box = text_box.get("box", {})
            rect = [
                int(box.get("x", 0) * sx),
                int(box.get("y", 0) * sy),
                int((box.get("x", 0) + box.get("w", 0)) * sx),
                int((box.get("y", 0) + box.get("h", 0)) * sy),
            ]
            warning = text_box.get("estimated_overflow_ratio", 0) > 1.2 or text_box.get("min_font_pt", 18) < 9
            fill = "#fff1f1" if warning else "#ffffff"
            outline = "#c43d3d" if warning else "#777777"
            draw.rectangle(rect, fill=fill, outline=outline, width=3)
            preview = str(text_box.get("preview", "")).strip()
            max_chars = max(12, int(max(rect[2] - rect[0], 80) / 9))
            lines = textwrap.wrap(preview, width=max_chars)[:6]
            y = rect[1] + 6
            for line in lines:
                if y > rect[3] - 14:
                    break
                safe_draw_text(draw, (rect[0] + 6, y), line, fill="#222222")
                y += 14
        for offset, warning in enumerate(slide.get("warnings", [])[:4]):
            safe_draw_text(draw, (16, height_px - 20 * (4 - offset)), warning[:180], fill="#b00020")
        output = out_dir / f"slide_{int(slide['index']):02d}_layout_preview.png"
        image.save(output)
        written.append(str(output.name))
    return written


def _generate_pptx_quality_artifacts(result_dir: Path) -> list[Path]:
    pptx_files = [
        path
        for path in sorted(result_dir.rglob("*.pptx"))
        if PPTX_QUALITY_DIR not in path.relative_to(result_dir).parts
    ]
    generated: list[Path] = []
    if not pptx_files:
        return generated
    quality_root = result_dir / PPTX_QUALITY_DIR
    quality_root.mkdir(parents=True, exist_ok=True)
    for pptx in pptx_files:
        out_dir = quality_root / pptx.stem
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        probe = _probe_pptx_layout(pptx)
        preview_files = _write_pptx_preview_images(probe, out_dir)
        probe["preview_images"] = preview_files
        write_local(out_dir / "quality_probe.json", json.dumps(probe, ensure_ascii=False, indent=2) + "\n")
        summary_lines = [
            f"# PPTX quality probe: {pptx.name}",
            "",
            f"- OpenXML readable: {probe.get('ok')}",
            f"- Slide count: {probe.get('slide_count')}",
            f"- Warning count: {probe.get('summary', {}).get('warning_count')}",
            f"- Slides with warnings: {probe.get('summary', {}).get('slides_with_warnings')}",
            f"- Layout preview images: {', '.join(preview_files) if preview_files else 'not generated'}",
            "",
            "This probe is a supervisor aid, not a full PowerPoint renderer. Use it together with the PPTX and any executor screenshots to judge overflow, density, figure placement, and template suitability.",
        ]
        for slide in probe.get("slides", []):
            if not slide.get("warnings"):
                continue
            summary_lines.append("")
            summary_lines.append(f"## Slide {slide['index']}")
            for warning in slide.get("warnings", [])[:8]:
                summary_lines.append(f"- {warning}")
        write_local(out_dir / "summary.md", "\n".join(summary_lines) + "\n")
        generated.extend([out_dir / "quality_probe.json", out_dir / "summary.md"])
        generated.extend(out_dir / name for name in preview_files)
    return generated
