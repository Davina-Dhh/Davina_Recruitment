# TalentRadar｜智能招聘情报 Agent（Davina）

产品层工作台说明。对外名称 **TalentRadar**，助手 / 出品品牌 **Davina**。

## 本机启动

```bash
cd dashboard
streamlit run davina_workbench.py --server.port 8501
```

## 服务器 / 外网

见 [DEPLOY.md](./DEPLOY.md)。Streamlit Cloud 入口文件：`dashboard/davina_workbench.py`。

## 功能

- 单公司精查 / 赛道批量扫  
- 公司池管理与门户一键接入  
- Agent 流程可视与运行回放  
- Agnes AI 岗位点评  
- 简历 PDF/Word × JD 匹配与优化建议  
- 感兴趣清单与导出  
- 系统内产品 PRD  
