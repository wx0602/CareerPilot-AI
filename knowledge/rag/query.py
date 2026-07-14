from __future__ import annotations

import argparse
import json

from knowledge.rag import KnowledgeService


def main() -> None:
    parser = argparse.ArgumentParser(description="查询 CareerPilot AI 知识库")
    parser.add_argument("query")
    parser.add_argument("--kind", choices=["questions", "materials"], default="questions")
    parser.add_argument("--database", default="knowledge/question_bank/questions.sqlite3")
    parser.add_argument("--chroma-dir", default="knowledge/chroma_store")
    parser.add_argument("--position")
    parser.add_argument("--difficulty")
    parser.add_argument("--type")
    parser.add_argument("--user-id")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    service = KnowledgeService(database_path=args.database, chroma_directory=args.chroma_dir)
    if args.kind == "questions":
        result = service.search_questions(
            args.query,
            position=args.position,
            difficulty=args.difficulty,
            question_type=args.type,
            top_k=args.top_k,
        )
    else:
        result = service.search_materials(
            args.query,
            user_id=args.user_id,
            material_type=args.type,
            top_k=args.top_k,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
