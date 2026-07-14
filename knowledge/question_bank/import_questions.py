from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge.question_bank.validation import load_and_clean_questions, save_questions
from knowledge.rag.service import KnowledgeService


def main() -> None:
    parser = argparse.ArgumentParser(description="清洗并导入 CareerPilot AI 题库")
    parser.add_argument("source", help="原始 JSON 题库路径")
    parser.add_argument("--database", default="knowledge/question_bank/questions.sqlite3")
    parser.add_argument("--cleaned", default="knowledge/question_bank/cleaned/questions.json")
    parser.add_argument("--rejected", default="knowledge/question_bank/cleaned/rejected.json")
    parser.add_argument("--chroma-dir", default="knowledge/chroma_store")
    parser.add_argument("--without-chroma", action="store_true")
    args = parser.parse_args()

    questions, rejected = load_and_clean_questions(args.source)
    save_questions(questions, args.cleaned)
    rejected_path = Path(args.rejected)
    rejected_path.parent.mkdir(parents=True, exist_ok=True)
    rejected_path.write_text(json.dumps(rejected, ensure_ascii=False, indent=2), encoding="utf-8")

    service = KnowledgeService(
        database_path=args.database,
        chroma_directory=None if args.without_chroma else args.chroma_dir,
    )
    result = service.import_questions(questions)
    result.update({"accepted": len(questions), "rejected": len(rejected)})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
