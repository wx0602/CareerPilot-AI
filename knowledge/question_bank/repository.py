from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable

from knowledge.models import QuestionOption, StoredQuestion


TABLE_NAME = "questions_v2"


class QuestionRepository:
    """SQLite题库。

    使用 v2 表名，避免覆盖按旧占位字段导入的数据。
    """

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.database_path.is_file():
            raise FileNotFoundError(f"题库数据库不存在：{self.database_path}")
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    question_id TEXT PRIMARY KEY,
                    company TEXT NOT NULL,
                    position TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    answer_json TEXT NOT NULL,
                    knowledge_points_json TEXT NOT NULL,
                    explanation TEXT,
                    source TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    license TEXT NOT NULL
                )
                """
            )
            connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_questions_v2_position ON {TABLE_NAME}(position)"
            )
            connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_questions_v2_filters "
                f"ON {TABLE_NAME}(difficulty, question_type)"
            )
            connection.commit()

    def upsert_many(self, questions: Iterable[StoredQuestion]) -> int:
        rows = [
            (
                q.question_id,
                q.company,
                q.position,
                q.difficulty,
                q.question_type,
                q.content,
                json.dumps([item.model_dump(mode="json") for item in q.options], ensure_ascii=False),
                json.dumps(q.answer, ensure_ascii=False),
                json.dumps(q.knowledge_points, ensure_ascii=False),
                q.explanation,
                q.source,
                q.source_url,
                q.license,
            )
            for q in questions
        ]
        with closing(self._connect()) as connection:
            connection.executemany(
                f"""
                INSERT INTO {TABLE_NAME} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(question_id) DO UPDATE SET
                    company=excluded.company,
                    position=excluded.position,
                    difficulty=excluded.difficulty,
                    question_type=excluded.question_type,
                    content=excluded.content,
                    options_json=excluded.options_json,
                    answer_json=excluded.answer_json,
                    knowledge_points_json=excluded.knowledge_points_json,
                    explanation=excluded.explanation,
                    source=excluded.source,
                    source_url=excluded.source_url,
                    license=excluded.license
                """,
                rows,
            )
            connection.commit()
        return len(rows)

    def list_questions(
        self,
        *,
        position: str | None = None,
        company: str | None = None,
        difficulty: str | None = None,
        question_type: str | None = None,
    ) -> list[StoredQuestion]:
        clauses: list[str] = []
        params: list[str] = []
        for column, value in (
            ("position", position),
            ("company", company),
            ("difficulty", difficulty),
            ("question_type", question_type),
        ):
            if value:
                clauses.append(f"{column} = ?")
                params.append(value)
        sql = f"SELECT * FROM {TABLE_NAME}"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY question_id"
        with closing(self._connect()) as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> StoredQuestion:
        return StoredQuestion(
            question_id=row["question_id"],
            company=row["company"],
            position=row["position"],
            difficulty=row["difficulty"],
            question_type=row["question_type"],
            content=row["content"],
            options=[QuestionOption.model_validate(item) for item in json.loads(row["options_json"])],
            answer=json.loads(row["answer_json"]),
            knowledge_points=json.loads(row["knowledge_points_json"]),
            explanation=row["explanation"],
            source=row["source"],
            source_url=row["source_url"],
            license=row["license"],
        )
