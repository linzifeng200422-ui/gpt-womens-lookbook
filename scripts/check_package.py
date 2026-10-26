#!/usr/bin/env python3
"""Read-only integrity verification tool for gpt-womens-lookbook package.

Verifies:
1. Basic YAML frontmatter and skill name without PyYAML dependency.
2. 18 pose pages in image-pose-index.json exist, pose IDs are unique,
   (page, figure_id) pairs are unique, normalized bounding boxes are valid,
   referenced pose page images exist, and per-page counts match.
3. 19 original images (01.webp - 19.webp) exist without symlinks.
4. Relative markdown links exist (handling anchors, line suffixes, URL encoding/spaces),
   with no machine-specific hardcoded paths or path escapes.
5. Emits structured report with exit 1 on errors, exit 0 on success.

Scope Note:
This script checks structural and reference integrity only.
It does NOT verify pose semantic accuracy, aesthetics, or image generation results.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path


def parse_simple_frontmatter(text: str) -> dict[str, str]:
    """Parse basic YAML frontmatter between leading '---' fences without PyYAML."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    frontmatter_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        frontmatter_lines.append(line)
    result = {}
    for line in frontmatter_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip().strip("\"'")
    return result


def parse_simple_yaml_mapping(text: str) -> dict[str, str]:
    """Extract top-level and indented key-values from simple YAML without PyYAML."""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip("\"'")
            if v:
                result[k] = v
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify structural integrity and reference consistency of gpt-womens-lookbook."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Root path of gpt-womens-lookbook package (default: auto-detected)",
    )
    parser.add_argument("--json", action="store_true", help="Output full report in JSON format")
    args = parser.parse_args()

    root = args.root.resolve()
    errors: list[str] = []
    checks: dict[str, object] = {
        "verification_scope": (
            "Structural and reference integrity only. "
            "Does not verify pose semantic accuracy, aesthetics, or image generation results."
        )
    }

    # 1. Frontmatter check (SKILL.md & agents/openai.yaml without PyYAML)
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        errors.append("Missing SKILL.md in package root")
    else:
        skill_text = skill_md.read_text(encoding="utf-8")
        fm = parse_simple_frontmatter(skill_text)
        skill_name = fm.get("name")
        checks["skill_name"] = skill_name
        if not skill_name:
            errors.append("SKILL.md frontmatter missing required 'name' field")
        elif skill_name != "gpt-womens-lookbook" and skill_name != root.name:
            errors.append(f"SKILL.md frontmatter name '{skill_name}' does not match expected package name")

    openai_yaml = root / "agents/openai.yaml"
    if openai_yaml.is_file():
        yaml_content = openai_yaml.read_text(encoding="utf-8")
        parsed_yaml = parse_simple_yaml_mapping(yaml_content)
        checks["openai_yaml_fields"] = list(parsed_yaml.keys())

    # 2. Check 19 original images in assets/pose-pages/
    pose_pages_dir = root / "assets/pose-pages"
    missing_pages: list[str] = []
    for i in range(1, 20):
        page_name = f"{i:02d}.webp"
        page_path = pose_pages_dir / page_name
        if not page_path.is_file():
            missing_pages.append(page_name)
    checks["expected_original_pages"] = 19
    checks["missing_original_pages"] = missing_pages
    if missing_pages:
        errors.append(f"Missing original pose pages in assets/pose-pages: {', '.join(missing_pages)}")

    # 3. Check for symlinks across the package
    symlinks = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_symlink()]
    checks["symlinks"] = symlinks
    if symlinks:
        errors.append(f"Distribution must contain real portable files, not symlinks: {', '.join(symlinks)}")

    # 4. Check image-pose-index.json
    index_path = root / "references/image-pose-index.json"
    checks["index_file_present"] = index_path.is_file()

    if not index_path.is_file():
        errors.append("Missing index file: references/image-pose-index.json")
    else:
        try:
            index_data = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Invalid JSON in references/image-pose-index.json: {exc}")
            index_data = None

        if isinstance(index_data, dict):
            pages_list = index_data.get("pages")
            poses_list = index_data.get("poses")
            meta = index_data.get("metadata", {})
            if isinstance(meta, dict) and "expected_pose_count" in meta:
                checks["metadata_expected_pose_count"] = meta.get("expected_pose_count")

            # Validate pages
            if not isinstance(pages_list, list):
                errors.append("Index root missing 'pages' array")
            else:
                checks["index_pages_count"] = len(pages_list)
                if len(pages_list) != 18:
                    errors.append(f"Index expected 18 action pages in 'pages' array, found {len(pages_list)}")

                # Check each page entry
                for p_entry in pages_list:
                    if isinstance(p_entry, dict):
                        p_file = p_entry.get("page")
                        declared_count = p_entry.get("count", p_entry.get("pose_count"))
                    else:
                        p_file = str(p_entry)
                        declared_count = None

                    if not p_file:
                        errors.append(f"Index page entry missing filename: {p_entry}")
                        continue

                    page_file_path = pose_pages_dir / p_file
                    if not page_file_path.is_file():
                        errors.append(f"Index references missing page file: assets/pose-pages/{p_file}")

                    if not isinstance(declared_count, int) or isinstance(declared_count, bool) or declared_count < 0:
                        errors.append(f"Page {p_file} missing or invalid declared count: {declared_count}")
                    elif isinstance(poses_list, list):
                        actual_for_page = sum(
                            1 for p in poses_list if isinstance(p, dict) and p.get("page") == p_file
                        )
                        if actual_for_page != declared_count:
                            errors.append(
                                f"Page {p_file} declared count={declared_count} but index has {actual_for_page} poses"
                            )

            # Validate poses
            if not isinstance(poses_list, list):
                errors.append("Index root missing 'poses' array")
            else:
                checks["index_poses_count"] = len(poses_list)
                if isinstance(meta, dict) and "expected_pose_count" in meta and len(poses_list) != meta["expected_pose_count"]:
                    errors.append(f"Expected {meta['expected_pose_count']} poses, found {len(poses_list)}")
                seen_ids: set[str] = set()
                seen_page_figs: set[tuple[str, str]] = set()

                for pose in poses_list:
                    if not isinstance(pose, dict):
                        errors.append(f"Invalid pose entry (not an object): {pose}")
                        continue

                    pid = str(pose.get("id", "")).strip()
                    if not pid:
                        errors.append("Pose entry missing 'id'")
                    elif pid in seen_ids:
                        errors.append(f"Duplicate pose id: '{pid}'")
                    else:
                        seen_ids.add(pid)

                    page = str(pose.get("page", "")).strip()
                    fig = str(pose.get("figure_id", "")).strip()
                    if not page:
                        errors.append(f"Pose {pid} missing 'page'")
                    else:
                        if not (pose_pages_dir / page).is_file():
                            errors.append(f"Pose {pid} references missing page: assets/pose-pages/{page}")

                    if not fig:
                        errors.append(f"Pose {pid} missing 'figure_id'")
                    elif page:
                        key = (page, fig)
                        if key in seen_page_figs:
                            errors.append(f"Duplicate (page, figure_id) combination in pose {pid}: {key}")
                        else:
                            seen_page_figs.add(key)

                    # Validate box
                    box = pose.get("box")
                    if not (isinstance(box, (list, tuple)) and len(box) == 4):
                        errors.append(f"Pose {pid} has invalid box format: {box}")
                    else:
                        try:
                            bx, by, bw, bh = (float(v) for v in box)
                            if bx < 0 or by < 0 or bw <= 0 or bh <= 0:
                                errors.append(f"Pose {pid} box coordinates must be positive numbers: {box}")
                            elif bx > 1.0 or by > 1.0 or bw > 1.0 or bh > 1.0:
                                errors.append(f"Pose {pid} box dimensions exceed 1.0: {box}")
                            elif (bx + bw) > 1.0001 or (by + bh) > 1.0001:
                                errors.append(f"Pose {pid} box extends beyond boundary [0, 1]: {box}")
                        except (ValueError, TypeError):
                            errors.append(f"Pose {pid} box coordinates are non-numeric: {box}")

    # 5. Check markdown relative links and hardcoded machine paths
    markdown_files = list(root.rglob("*.md"))
    checks["markdown_files_checked"] = len(markdown_files)
    markdown_links_checked = 0

    abs_path_pattern = re.compile(r"(?:/Users/[^\s\)\"\'`]+|/home/[^\s\)\"\'`]+|[A-Za-z]:\\[^\s\)\"\'`]+)")

    for md_path in markdown_files:
        try:
            content = md_path.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"Failed to read markdown file {md_path.relative_to(root)}: {exc}")
            continue

        # Check for hardcoded machine absolute paths
        for match in abs_path_pattern.findall(content):
            errors.append(
                f"Machine-specific hardcoded absolute path in {md_path.relative_to(root)}: {match}"
            )

        # Check relative markdown links: [text](target)
        for link_match in re.finditer(r"\[(?:[^\]]*)\]\(([^)]+)\)", content):
            raw_target = link_match.group(1).strip()
            # Ignore absolute URLs, mailto, anchor-only links
            if re.match(r"^(?:https?://|mailto:|#)", raw_target):
                continue

            target = raw_target.strip("<>")
            # Handle URL decoding (spaces as %20 or actual spaces)
            target = urllib.parse.unquote(target)
            # Remove fragment/anchor (#anchor or #L10-L20)
            target = target.split("#")[0]
            # Remove line number suffixes (:10 or :10:20)
            target = re.sub(r":\d+(?::\d+)?$", "", target)

            if not target:
                continue

            markdown_links_checked += 1
            resolved = (md_path.parent / target).resolve()

            if not resolved.is_relative_to(root):
                errors.append(
                    f"Nonportable link in {md_path.relative_to(root)} escapes package root: {raw_target}"
                )
            elif not resolved.exists():
                errors.append(
                    f"Broken relative link in {md_path.relative_to(root)}: {raw_target}"
                )

    checks["markdown_links_checked"] = markdown_links_checked
    checks["errors"] = errors
    checks["ok"] = len(errors) == 0

    if args.json:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    else:
        status_label = "PASSED" if checks["ok"] else "FAILED"
        print(f"Package Check [{status_label}]: {len(errors)} error(s)")
        print(f"  Skill Name: {checks.get('skill_name')}")
        print(f"  Original 19 Pages: {'OK' if not missing_pages else 'MISSING ' + str(missing_pages)}")
        print(f"  Symlinks: {len(symlinks)}")
        print(f"  Markdown Files Checked: {checks.get('markdown_files_checked')}")
        print(f"  Markdown Links Checked: {checks.get('markdown_links_checked')}")
        if checks.get("index_file_present"):
            print(f"  Index Pages: {checks.get('index_pages_count')}")
            print(f"  Index Poses: {checks.get('index_poses_count')}")
            if "metadata_expected_pose_count" in checks:
                print(f"  Metadata Expected Pose Count: {checks.get('metadata_expected_pose_count')}")
        else:
            print("  Index: references/image-pose-index.json is missing")

        print(f"\nScope: {checks['verification_scope']}")

        if errors:
            print("\nErrors encountered:")
            for err in errors:
                print(f"  - {err}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
