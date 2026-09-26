# TalentRadar｜智能招聘情报 Agent（Davina）

多源招聘情报工作台。支持本机调试与公网访问；含 Agnes AI 岗位点评、简历匹配与产品 PRD。

## 本机启动

```bash
cd dashboard
streamlit run davina_workbench.py --server.port 8501
```

## 功能

- TalentRadar：多源拉岗、赛道扫描、Agent 流程回放  
- Davina：产品形象与交互工作台  
- AI 点评 / 简历×JD 匹配（Agnes 2.5 Flash）  
- 感兴趣清单与导出  

详见仓库根目录 README 与 `docs/PRD.md`。
