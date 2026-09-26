# Davina 秋招工作台

多源招聘情报工作台。支持本机调试与服务器公网访问；含 Agnes AI 岗位点评与产品 PRD。

## 本机启动

```bash
cd Hiring-Radar/dashboard
streamlit run davina_workbench.py --server.port 8501
```

打开 http://localhost:8501

## 服务器 / 外网访问

见 [DEPLOY.md](./DEPLOY.md)。核心是监听 `0.0.0.0` 并放行端口：

```bash
streamlit run davina_workbench.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

## 功能

- 默认单公司精查；可按赛道批量扫
- 公司池：已接入 / 全库添加 / 手动登记未入库名称
- 岗位可「加入感兴趣」，右侧与清单页可维护
- **AI 点评**（Agnes 2.5 Flash）：按画像打分、匹配点、缺口与投递建议
- **简历匹配**：上传 PDF/Word，对照 JD 评估匹配度并给出优化建议
- **产品 PRD**：侧栏或首页可跳转阅读 / 下载
- 导出 JSON / CSV

数据层基于 Hiring-Radar；界面与工作流为 Davina 产品层；大模型调用走 Agnes OpenAI 兼容 API。
