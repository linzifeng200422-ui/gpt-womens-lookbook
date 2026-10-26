#!/usr/bin/env python3
"""Offline query and bounding-box crop tool for gpt-womens-lookbook pose index.

Standard queries use only the Python standard library.
Pillow is only imported on demand when --crop-output is specified.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def get_default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize_page_query(query_page: str) -> str:
    qp = query_page.strip()
    if qp.endswith(".webp"):
        qp = qp[:-5]
    if qp.isdigit():
        return f"{int(qp):02d}.webp"
    return f"{qp}.webp"


def match_page(item_page: str, query_page: str) -> bool:
    ip = str(item_page).strip()
    qp = str(query_page).strip()
    if ip == qp:
        return True
    return normalize_page_query(ip) == normalize_page_query(qp)


def match_figure_id(item_fig: str, query_fig: str) -> bool:
    item_s = str(item_fig).strip()
    query_s = str(query_fig).strip()
    if item_s == query_s:
        return True
    if item_s.isdigit() and query_s.isdigit():
        return int(item_s) == int(query_s)
    return False


def build_searchable_text(item: dict) -> str:
    parts = [
        str(item.get("id", "")),
        str(item.get("figure_id", "")),
        str(item.get("action_family", "")),
        str(item.get("pose_zh", "")),
        str(item.get("gaze_zh", "")),
        str(item.get("expression_zh", "")),
        str(item.get("hands_zh", "")),
        str(item.get("outfit_visible_zh", "")),
    ]
    unc = item.get("uncertainties")
    if isinstance(unc, list):
        parts.extend(str(u) for u in unc)
    elif unc:
        parts.append(str(unc))
    return " ".join(parts).lower()


def perform_crop(
    item: dict,
    root: Path,
    output_path: Path,
) -> tuple[bool, str]:
    if output_path.exists():
        return False, f"Refusing to overwrite existing output file: {output_path}"
    if not output_path.parent.is_dir():
        return False, f"Parent directory does not exist: {output_path.parent}"

    # Lazy import Pillow only when cropping is requested
    try:
        from PIL import Image
    except ImportError:
        return False, "Pillow is required for --crop-output. Please ensure Pillow is installed."

    page_file = item.get("page")
    if not page_file:
        return False, f"Pose entry {item.get('id')} has no page field."

    source_path = root / "assets/pose-pages" / page_file
    if not source_path.is_file():
        return False, f"Source image file does not exist: {source_path}"

    box = item.get("box")
    if not (isinstance(box, (list, tuple)) and len(box) == 4):
        return False, f"Invalid box definition in pose {item.get('id')}: {box}"

    try:
        x, y, w, h = (float(v) for v in box)
    except (ValueError, TypeError):
        return False, f"Box coordinates must be valid numbers: {box}"

    if x < 0 or y < 0 or w <= 0 or h <= 0 or (x + w) > 1.0001 or (y + h) > 1.0001:
        return False, f"Box coordinates out of normalized bounds [0, 1]: {box}"

    try:
        with Image.open(source_path) as img:
            img_w, img_h = img.size
            left = max(0, min(img_w, int(round(x * img_w))))
            top = max(0, min(img_h, int(round(y * img_h))))
            right = max(left + 1, min(img_w, int(round((x + w) * img_w))))
            bottom = max(top + 1, min(img_h, int(round((y + h) * img_h))))
            cropped = img.crop((left, top, right, bottom))
            cropped.save(output_path)
    except Exception as exc:
        return False, f"Failed to crop and save image: {exc}"

    return True, (
        f"Cropped visible region for pose '{item.get('id')}' saved to: {output_path}\n"
        "Notice: Crop boundary / boundaries are derived from manual rough bounding boxes and require visual inspection. "
        "No inpainting, leg completion, or tag/neighbor stripping is performed."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query bundled pose index and optionally crop visible pose regions."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=get_default_root(),
        help="Root path of the gpt-womens-lookbook package (default: auto-detected)",
    )
    parser.add_argument("--id", help="Exact composite pose ID, e.g. p01-f001")
    parser.add_argument(
        "--figure-id",
        help="Printed figure number, e.g. 001. Multiple matches across pages are preserved.",
    )
    parser.add_argument("--page", help="Page selector, e.g. '01' or '01.webp'")
    parser.add_argument(
        "--framing",
        choices=("full", "half", "close"),
        help="Shot framing category (full, half, close)",
    )
    parser.add_argument("--action", help="Action family keyword or name")
    parser.add_argument(
        "--search",
        help="Chinese full-text keyword search across pose descriptions, gaze, expressions, and outfits",
    )
    parser.add_argument("--limit", type=int, help="Limit number of returned results (positive integer)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument(
        "--crop-output",
        type=Path,
        help="Crop matching pose visible region to a new PNG. Requires exactly 1 match; will not overwrite existing file.",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be a positive integer (>= 1)")

    root = args.root.resolve()
    index_path = root / "references/image-pose-index.json"

    if not index_path.is_file():
        msg = f"Index file not found: {index_path}. The complete skill package must include references/image-pose-index.json."
        if args.json:
            print(json.dumps({"error": msg, "matched": 0, "returned": 0, "items": []}, ensure_ascii=False, indent=2))
        else:
            sys.stderr.write(f"Error: {msg}\n")
        return 1

    try:
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:
        msg = f"Failed to parse index JSON at {index_path}: {exc}"
        if args.json:
            print(json.dumps({"error": msg, "matched": 0, "returned": 0, "items": []}, ensure_ascii=False, indent=2))
        else:
            sys.stderr.write(f"Error: {msg}\n")
        return 2

    poses = index_data.get("poses")
    if not isinstance(poses, list):
        msg = "Index root does not contain a valid 'poses' array."
        if args.json:
            print(json.dumps({"error": msg, "matched": 0, "returned": 0, "items": []}, ensure_ascii=False, indent=2))
        else:
            sys.stderr.write(f"Error: {msg}\n")
        return 2

    # Filter with intersection (AND) logic
    matched: list[dict] = []
    for item in poses:
        if not isinstance(item, dict):
            continue

        if args.id:
            wanted_id = args.id.strip().lower()
            actual_id = str(item.get("id", "")).strip().lower()
            if actual_id != wanted_id:
                continue

        if args.figure_id:
            if not match_figure_id(str(item.get("figure_id", "")), args.figure_id):
                continue

        if args.page:
            if not match_page(str(item.get("page", "")), args.page):
                continue

        if args.framing:
            if str(item.get("framing", "")).strip().lower() != args.framing.strip().lower():
                continue

        if args.action:
            action_query = args.action.strip().lower()
            actual_action = str(item.get("action_family", "")).strip().lower()
            if action_query != actual_action and action_query not in actual_action:
                continue

        if args.search:
            searchable = build_searchable_text(item)
            if args.search.strip().lower() not in searchable:
                continue

        # Prepare verified output item without fabricating unknown fields
        out_item = dict(item)
        page_val = item.get("page", "")
        rel_path = f"assets/pose-pages/{page_val}" if page_val else ""
        out_item["relative_path"] = rel_path
        out_item["absolute_path"] = str(root / rel_path) if rel_path else ""

        matched.append(out_item)

    total_matched = len(matched)
    returned_items = matched[: args.limit] if args.limit else matched

    crop_note = None
    if args.crop_output:
        if total_matched != 1:
            msg = f"--crop-output requires exactly 1 matching pose, but found {total_matched} matches."
            if args.json:
                print(
                    json.dumps(
                        {"error": msg, "matched": total_matched, "returned": len(returned_items), "items": returned_items},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                sys.stderr.write(f"Error: {msg}\n")
            return 2 if total_matched > 1 else 1

        target_pose = matched[0]
        ok, crop_msg = perform_crop(target_pose, root, args.crop_output.resolve())
        if not ok:
            if args.json:
                print(
                    json.dumps(
                        {"error": crop_msg, "matched": total_matched, "returned": len(returned_items), "items": returned_items},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                sys.stderr.write(f"Error: {crop_msg}\n")
            return 2
        crop_note = crop_msg

    if args.json:
        payload = {
            "matched": total_matched,
            "returned": len(returned_items),
            "items": returned_items,
        }
        if total_matched == 0:
            payload["note"] = "No matching poses found. Filters were not relaxed; check arguments or query index."
        if crop_note:
            payload["crop_output"] = str(args.crop_output.resolve())
            payload["crop_note"] = crop_note
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if total_matched > 0 else 1

    # Human-readable output
    if total_matched == 0:
        print("No matching poses found for the given criteria. (Filters were not relaxed)")
        return 1

    print(f"Matched {total_matched} pose(s), returning {len(returned_items)}:")
    print("-" * 64)
    for it in returned_items:
        print(
            f"[{it.get('id')}] Page: {it.get('page')} | Figure: {it.get('figure_id')} | "
            f"Framing: {it.get('framing')} | Action: {it.get('action_family')}"
        )
        if it.get("pose_zh"):
            print(f"  Pose (ZH):       {it.get('pose_zh')}")
        if it.get("gaze_zh"):
            print(f"  Gaze (ZH):       {it.get('gaze_zh')}")
        if it.get("expression_zh"):
            print(f"  Expression (ZH): {it.get('expression_zh')}")
        if it.get("hands_zh"):
            print(f"  Hands (ZH):      {it.get('hands_zh')}")
        if it.get("outfit_visible_zh"):
            print(f"  Outfit (ZH):     {it.get('outfit_visible_zh')}")
        if it.get("uncertainties"):
            print(f"  Uncertainties:   {it.get('uncertainties')}")
        print(f"  Box (norm):      {it.get('box')}")
        print(f"  Relative Path:   {it.get('relative_path')}")
        print(f"  Absolute Path:   {it.get('absolute_path')}")
        print("-" * 64)

    if crop_note:
        print(crop_note)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
