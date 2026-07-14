from __future__ import annotations

import argparse
import json

from knowledge.parsers import parse_material


def main() -> None:
    parser = argparse.ArgumentParser(description="解析简历、JD、项目介绍、计划书或路演 PPT")
    parser.add_argument("path")
    parser.add_argument(
        "--type",
        required=True,
        choices=["resume", "jd", "project_intro", "business_plan", "pitch_ppt", "pitch_deck"],
        help="pitch_deck 是旧名称，会自动转换为公共模型使用的 pitch_ppt",
    )
    parser.add_argument("--user-id", default="guest")
    parser.add_argument("--output")
    args = parser.parse_args()
    material = parse_material(args.path, material_type=args.type, user_id=args.user_id)
    output = json.dumps(material.to_dict(), ensure_ascii=False, indent=2)
    if args.output:
        from pathlib import Path

        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
