import sqlite3
import tempfile
import unittest
from pathlib import Path

from models import ContextChunk, QuestionBankItem

from knowledge.question_bank.validation import clean_questions, load_and_clean_questions
from knowledge.rag.service import KnowledgeService


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "question_bank" / "raw" / "seed_questions.json"


class QuestionBankTests(unittest.TestCase):
    def test_seed_bank_is_valid_and_covers_all_positions(self):
        questions, rejected = load_and_clean_questions(SEED)
        self.assertEqual(rejected, [])
        self.assertEqual(len(questions), 24)
        self.assertEqual(
            {item.position for item in questions},
            {
                "general",
                "java_backend",
                "python_backend",
                "frontend",
                "software_testing",
                "data_ai",
                "devops",
                "product_operation",
            },
        )

    def test_duplicate_id_is_rejected(self):
        raw = {
            "question_id": "same",
            "company": "通用",
            "position": "general",
            "difficulty": "easy",
            "question_type": "true_false",
            "content": "这是测试题吗？",
            "options": [],
            "answer": "true",
            "knowledge_points": ["测试"],
            "explanation": "用于测试。",
        }
        cleaned, rejected = clean_questions([raw, {**raw, "content": "另一道题"}])
        self.assertEqual(len(cleaned), 1)
        self.assertIn("重复题号", rejected[0]["reason"])

    def test_multiple_choice_uses_shared_answer_and_option_format(self):
        raw = {
            "question_id": "multi_001",
            "company": "通用",
            "position": "general",
            "difficulty": "medium",
            "question_type": "multiple_choice",
            "content": "以下哪些属于关系型数据库？",
            "options": [
                {"key": "A", "text": "MySQL"},
                {"key": "B", "text": "PostgreSQL"},
                {"key": "C", "text": "Redis"},
            ],
            "answer": ["A", "B"],
            "knowledge_points": ["数据库"],
            "explanation": "MySQL和PostgreSQL属于关系型数据库。",
        }
        cleaned, rejected = clean_questions([raw])
        self.assertEqual(rejected, [])
        public = cleaned[0].to_bank_item()
        self.assertEqual(public.answer, ["A", "B"])
        self.assertEqual(public.options[0].key, "A")

    def test_import_and_filter_search(self):
        questions, _ = load_and_clean_questions(SEED)
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "questions.sqlite3"
            sqlite3.connect(database_path).close()
            service = KnowledgeService(database_path=database_path)
            result = service.import_questions(questions)
            self.assertEqual(result["imported"], 24)
            search = service.search_questions("缓存", position="java_backend", top_k=5)
            self.assertEqual(search["total"], 1)
            self.assertEqual(search["questions"][0]["question_id"], "seed_java_003")
            self.assertEqual(search["contexts"][0]["chunk_id"], "seed_java_003")
            QuestionBankItem.model_validate(search["questions"][0])
            ContextChunk.model_validate(search["contexts"][0])

            public_search = service.search_questions(
                "缓存", position="java_backend", include_answer=False
            )
            self.assertIsNone(public_search["questions"][0]["answer"])
            self.assertIsNone(public_search["questions"][0]["explanation"])


if __name__ == "__main__":
    unittest.main()
