# TalentRadar｜智能招聘情报 Agent（Davina）

多源校园招聘情报工作台：自动拉岗 · Agent 流程可视 · Agnes AI 点评 · 简历×JD 匹配。  
对外产品名 **TalentRadar**，出品与助手品牌 **Davina**。

## 在线体验

部署到 Streamlit Community Cloud 后，将在此更新公网链接。

## 本机运行

```bash
cd dashboard
pip install -r requirements.txt
streamlit run davina_workbench.py
```

打开 http://localhost:8501

## Streamlit Cloud 部署

1. 使用本仓库 `Davina-Dhh/Davina_Recruitment`  
2. 打开 [share.streamlit.io](https://share.streamlit.io) → New app  
3. Main file path：`dashboard/davina_workbench.py`  
4. 密钥：仓库内 `dashboard/.env`，或在 Cloud Secrets 中配置：

```toml
AGNES_API_KEY = "你的密钥"
AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"
AGNES_MODEL = "agnes-2.5-flash"
```

推送 `main` 后 Cloud 一般会自动重新部署；也可在控制台手动 Reboot。

## 目录说明

| 路径 | 说明 |
| --- | --- |
| `dashboard/` | TalentRadar / Davina 产品层（界面、AI、简历、PRD） |
| `parsers/` | ATS 解析器与公司种子表 |
| `hiring_radar.py` | 开源 Hiring-Radar 数据层 |

产品 PRD 见 `dashboard/docs/PRD.md`，部署说明见 `dashboard/DEPLOY.md`。
