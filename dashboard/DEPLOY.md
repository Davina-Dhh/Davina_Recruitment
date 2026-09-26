# TalentRadar / Davina · 服务器部署说明

## 本机调试

```bash
cd dashboard
streamlit run davina_workbench.py --server.port 8501
```

## 服务器最小部署

```bash
streamlit run davina_workbench.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true
```
