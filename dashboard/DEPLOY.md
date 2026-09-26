# Davina 秋招工作台 · 服务器部署说明

## 目标

让外网用户通过浏览器访问工作台（例如 `http://你的服务器IP:8501` 或绑定域名 + HTTPS）。

## 本机调试

```bash
cd Hiring-Radar/dashboard
streamlit run Davina秋招工作台.py --server.port 8501
```

## 服务器最小部署

1. 把项目拷到服务器（或 git clone）
2. 安装 Python 3.10+，进入 `dashboard`：
   ```bash
   pip install -r requirements.txt
   ```
3. 配置密钥（勿提交 Git）：
   ```bash
   cp .env.example .env
   # 编辑 .env，填入 AGNES_API_KEY
   ```
4. 监听所有网卡，供外网访问：
   ```bash
   streamlit run Davina秋招工作台.py \
     --server.address 0.0.0.0 \
     --server.port 8501 \
     --server.headless true
   ```
5. 云厂商安全组 / 防火墙放行 **8501**（或前面用 Nginx 反代 80/443）

## Docker（可选）

在 `dashboard` 目录：

```bash
docker build -t davina-qiuzhao .
docker run -d --name davina -p 8501:8501 --env-file .env davina-qiuzhao
```

## 注意

- Agnes Key 只放服务器环境变量 / `.env`，不要写进前端或公开仓库  
- 当前 `user_prefs.json` 为单机文件存储，适合演示；多用户隔离可后续再做  
- 建议生产用 Nginx + HTTPS，反代到 `127.0.0.1:8501`  
