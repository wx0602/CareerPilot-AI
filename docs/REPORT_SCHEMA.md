# 报告 JSON 约定

本文件由 D 主导维护，B 用于接口响应，A 用于页面展示。

```json
{
  "overall_score": 82,
  "dimension_scores": {
    "专业知识": 80,
    "逻辑表达": 85,
    "岗位匹配": 78
  },
  "weaknesses": [
    "Redis 缓存机制",
    "MySQL 索引"
  ],
  "suggestions": [
    "建议复习缓存穿透和索引失效场景"
  ]
}
```

## 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `overall_score` | number | 总分 |
| `dimension_scores` | object | 分项评分 |
| `weaknesses` | string[] | 薄弱点 |
| `suggestions` | string[] | 改进建议 |

## 第一阶段展示范围

- 总分
- 分项评分
- 错题薄弱点
- 文本改进建议
