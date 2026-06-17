# 飞牛 NAS 部署指南

> 把"个人 AI 知识库"后端部署到你家里的飞牛 NAS（fnOS）上，让 Windows 客户端随时能连。

## 📋 准备工作

### 硬件
- 飞牛 NAS 一台（x86 架构，2 核 2G 内存就够）
- 公网 IPv6（国内三大运营商都默认开，打电话客服也能开）
- 域名一个（腾讯云/阿里云，约 80 元/年，可省——用 DDNS）

### 软件
- 飞牛 fnOS 0.8+（应用中心能装 Docker）
- DeepSeek API key（[申请](https://platform.deepseek.com/)）
- （可选）DashScope API key（[阿里云百炼](https://dashscope.console.aliyun.com/)，免费额度够个人用）

---

## 🚀 部署步骤

### 1. 飞牛 NAS 初始化

1. 装好 fnOS，进控制台
2. **应用中心** → 搜索 `Container` 或 `Docker` → 安装
3. **设置** → **系统设置** → **终端机** → 开启 SSH
4. 创建数据目录：
   ```bash
   mkdir -p /vol1/1000/kb-data/{sqlite,chroma,logs,ssl}
   ```

### 2. 上传后端代码（两种方式任选）

#### 方式 A：Git 拉取（推荐）
```bash
ssh admin@<NAS-IP>
cd /vol1/1000/docker
git clone https://github.com/yourname/knowledge-base.git
cd knowledge-base/backend
```

#### 方式 B：本地构建后上传
在 Windows 上：
```bash
cd knowledge-base
docker build -t kb-backend:latest ./backend
docker save kb-backend:latest | gzip > kb-backend.tar.gz
scp kb-backend.tar.gz admin@<NAS-IP>:/vol1/1000/docker/
```

NAS 上导入镜像：
```bash
ssh admin@<NAS-IP>
docker load < /vol1/1000/docker/kb-backend.tar.gz
```

### 3. 配 .env

```bash
cd /vol1/1000/docker/knowledge-base/backend
cp .env.example .env
nano .env
```

**必须改的**：
```env
# 把开发占位符都替换掉
JWT_SECRET=<64 字符随机串，运行 `openssl rand -hex 32` 生成>
DEEPSEEK_API_KEY=sk-你的真实 key
DASHSCOPE_API_KEY=sk-你的真实 key（没有就空着）

# 容器内的路径（**不要改**）
DATA_DIR=/app/data
SQLITE_PATH=/app/data/sqlite/kb.db
CHROMA_PATH=/app/data/chroma
```

### 4. 启动后端

```bash
docker compose up -d
docker compose ps
```

**预期输出**：
```
NAME           STATUS          PORTS
kb-backend     Up 2 minutes    0.0.0.0:8000->8000/tcp
```

### 5. 验证

```bash
# 健康检查
curl http://127.0.0.1:8000/api/health
# 期望：{"status":"ok",...}

# 防火墙放行（飞牛控制台 → 系统 → 防火墙）
# 允许入站 TCP 8000 (IPv4) 和 8000 (IPv6)
```

---

## 🌐 外网访问（IPv6 + DDNS）

> 没有域名也能用：直接把 NAS 的 IPv6 填到客户端 API 地址里。但有域名方便记忆。

### 1. 域名 + DDNS

#### 腾讯云 DDNS
```bash
# 1. 申请 API Token：腾讯云控制台 → 访问管理 → API 密钥管理
#    给 DNSPod 权限

# 2. NAS 上用 Docker 跑 ddns-go
docker run -d --name ddns-go --restart=always \
  -p 9876:9876 \
  -v /vol1/1000/docker/ddns-go:/root \
  jeessy2/ddns-go

# 3. 访问 http://<NAS-IP>:9876 配置
#    选腾讯云 → 填 Token → 添加 api.yourdomain.com 记录
#    类型 AAAA（IPv6）
```

#### 阿里云 DDNS
类似流程，DDNS-go 也支持。

### 2. 飞牛防火墙开端口（IPv6）

fnOS 控制台 → **网络** → **防火墙** → 添加规则：
- 协议：TCP
- 端口：8000
- 来源：::/0（IPv6 全网）
- 动作：放行

### 3. 路由器防火墙（如果上面的还不够）

部分路由器（小米/华为）默认禁止 IPv6 入站：
- 路由器后台 → 防火墙 → 关闭"IPv6 防火墙"或"阻止外部 IPv6 主动连接"
- 飞牛 NAS 设为 IPv6 防火墙放行

### 4. 测试外网访问

```bash
# 在外面（手机 4G/5G）打开：
curl -6 https://api.yourdomain.com/api/health
```

---

## 🔒 HTTPS（推荐）

> 不配 HTTPS，浏览器/小程序会拒绝访问；Windows 客户端没事（用 HTTP 也能跑）。

### 用 Caddy（自动 HTTPS）

```bash
docker run -d --name caddy --restart=always \
  -p 80:80 -p 443:443 \
  -v /vol1/1000/docker/caddy/Caddyfile:/etc/caddy/Caddyfile \
  -v /vol1/1000/kb-data/ssl:/ssl \
  caddy:2
```

`Caddyfile`：
```
api.yourdomain.com {
    reverse_proxy 127.0.0.1:8000
    encode gzip
    # 启用 SSE 必需
    reverse_proxy 127.0.0.1:8000 {
        flush_interval -1
    }
}
```

Caddy 会自动从 Let's Encrypt 申请证书，90 天自动续。

---

## 💾 备份

### 1. 群晖 Hyper Backup 替代方案（飞牛）

飞牛自带备份工具（如果有的话），或者用 cron + rclone 同步到云盘：

```bash
# 创建备份脚本
cat > /vol1/1000/docker/backup-kb.sh <<'EOF'
#!/bin/bash
BACKUP_DIR=/vol1/1000/backups/kb
DATE=$(date +%Y%m%d-%H%M)
mkdir -p $BACKUP_DIR

# 停后端
cd /vol1/1000/docker/knowledge-base
docker compose stop backend

# 打包
tar czf $BACKUP_DIR/kb-$DATE.tar.gz \
    backend/data/

# 启后端
docker compose start backend

# 保留最近 30 份
cd $BACKUP_DIR
ls -t kb-*.tar.gz | tail -n +31 | xargs rm -f

# 同步到云盘（如果你用 rclone 配置过）
# rclone copy $BACKUP_DIR/kb-$DATE.tar.gz remote:kb-backup/

echo "Backup done: kb-$DATE.tar.gz"
EOF
chmod +x /vol1/1000/docker/backup-kb.sh

# 加 cron 任务：每天凌晨 3 点
crontab -e
# 添加：
0 3 * * * /vol1/1000/docker/backup-kb.sh >> /var/log/kb-backup.log 2>&1
```

### 2. 备份频率建议

- **重要笔记**：每天全量（上面脚本）
- **聊天历史**：每周（看个人需求）
- **配置**：每次改 .env 后手动复制一份

---

## 📊 监控

### 简单方案：Log Center + 邮件告警

飞牛 → 应用中心 → 安装 **Log Center**（如有）

### 看实时日志

```bash
docker logs -f kb-backend
```

### 健康检查

```bash
# 加到 cron，每 5 分钟检查一次
*/5 * * * * curl -sf http://127.0.0.1:8000/api/health || echo "kb-backend DOWN $(date)" >> /var/log/kb-health.log
```

---

## 🔧 故障排查

### 容器起不来

```bash
docker logs kb-backend
# 看最后 30 行找错误
```

常见原因：
1. **端口被占**：改 `docker-compose.yml` 里 `8000:8000` 第一个数字
2. **数据目录权限**：`chmod -R 777 /vol1/1000/kb-data`
3. **chromadb 装不上**：检查 Python 版本，`docker exec kb-backend python --version`

### 客户端连不上

1. **在 NAS 上 curl 测**：`curl http://127.0.0.1:8000/api/health` → 应该 200
2. **Windows 上 curl 测 NAS IP**：`curl http://192.168.1.100:8000/api/health`
3. **外网测**：`curl -6 https://api.yourdomain.com/api/health`
4. 任何一步失败 → 检查防火墙

### AI 不工作

1. 测 key 有效性：
   ```bash
   curl https://api.deepseek.com/v1/chat/completions \
     -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}]}'
   ```
2. 看后端日志：`docker logs kb-backend | grep -i "error"`
3. 余额不足：`https://platform.deepseek.com/usage`

### 向量检索不工作（AI 答非所问）

1. 确认 DashScope key 配了
2. 重启后端触发重新向量化：
   ```bash
   docker compose restart backend
   ```
3. 重建向量库（删 chroma 目录）：
   ```bash
   docker compose down
   rm -rf /vol1/1000/kb-data/chroma/*
   docker compose up -d
   # 然后重新编辑每条笔记触发向量化
   ```

---

## 📈 升级

```bash
cd /vol1/1000/docker/knowledge-base
git pull  # 如果用 Git
docker compose build --no-cache
docker compose up -d
```

数据在 `data/` 目录，**升级不会丢**。

---

## 🔐 安全建议

1. **JWT_SECRET 必须改**：64 字符随机串
2. **不要用 8000 端口对外**：套 Caddy 或 Nginx
3. **定期更新**：每月 `git pull` + `docker compose build`
4. **CORS**：生产环境改为具体域名：
   ```env
   CORS_ORIGINS=["https://app.yourdomain.com"]
   ```
5. **不要开 v1 单用户多用户**：v1 假设单用户，密码就是你的唯一入口

---

## 🆚 与云服务器对比

| 维度 | 飞牛 NAS | 云服务器（2C4G）|
|---|---|---|
| 月成本 | 10-20 元（电费）| 100-150 元 |
| 数据主权 | 完全在你家 | 在云厂商 |
| 公网访问 | 需要 IPv6 + DDNS | 自带公网 IP |
| 性能 | 一般 | 强 |
| 部署难度 | 中等（需穿透）| 简单 |
| 备份 | RAID + 异地同步 | 快照 |

> 飞牛方案适合：注重隐私、笔记量个人级别（< 10 万条）、对速度不敏感。
> 云服务器适合：需要公网稳定访问、想给朋友用、笔记量很大。

---

## 📞 紧急救援

如果整个系统崩了：

```bash
# 1. SSH 进 NAS
ssh admin@<NAS-IP>

# 2. 停所有容器
docker compose down

# 3. 从备份恢复
ls /vol1/1000/backups/kb/
tar xzf /vol1/1000/backups/kb/kb-20260615-0300.tar.gz -C /

# 4. 重新启动
cd /vol1/1000/docker/knowledge-base
docker compose up -d

# 5. 验证
curl http://127.0.0.1:8000/api/health
```

5 分钟恢复，前提是有定期备份。
