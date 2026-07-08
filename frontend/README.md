# A 工作区：前端与数字人展示

本目录归 A 负责，当前只提供 Vue 3 + Vite 页面框架，不包含真实业务逻辑。

## 页面占位

- 登录 / 游客模式：`src/pages/LoginPage.vue`
- 场景选择：`src/pages/DashboardPage.vue`
- 材料上传：`src/pages/UploadPage.vue`
- 企业笔试：`src/pages/WrittenExamPage.vue`
- 文本面试：`src/pages/TextInterviewPage.vue`
- 综合报告：`src/pages/ReportPage.vue`
- 数字人展示：`src/pages/AvatarPage.vue`

## 对接约定

- 接口字段先看 `../docs/API_CONTRACT.md`
- 报告结构先看 `../docs/REPORT_SCHEMA.md`
- 假数据建议统一放在 `../shared/mock-data/`

## 本地运行

从仓库根目录运行：

```bash
npm install
npm run dev
```
