# Davina 秋招工作台（Davina Recruitment）

多源校园招聘情报工作台：自动拉岗 · Agent 流程可视 · Agnes AI 点评 · 简历×JD 匹配。

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

1. Fork / 使用本仓库  
2. 打开 [share.streamlit.io](https://share.streamlit.io) → New app  
3. Main file path：`dashboard/davina_workbench.py`  
4. Secrets 中配置：

```toml
AGNES_API_KEY = "你的密钥"
AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"
AGNES_MODEL = "agnes-2.5-flash"
```

## 目录说明

| 路径 | 说明 |
| --- | --- |
| `dashboard/` | Davina 产品层（界面、AI、简历、PRD） |
| `parsers/` | ATS 解析器与公司种子表 |
| `hiring_radar.py` | 开源 Hiring-Radar 数据层 |

产品 PRD 见 `dashboard/docs/PRD.md`，部署说明见 `dashboard/DEPLOY.md`。

## 声明

岗位数据来自公开招聘门户，仅供求职辅助；请遵守目标站点使用规范。Agnes API Key 请自行配置，勿提交到仓库。
