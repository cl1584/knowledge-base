#!/usr/bin/env bash
# ==============================================================
# 个人 AI 知识库 - NAS 一键安装脚本
# 适用：飞牛 fnOS / Debian / Ubuntu / 其他 Linux NAS
# 作用：拉后端镜像 + 起容器 + 配 .env + 配反代 + 配 DDNS 提示
# ==============================================================
set -euo pipefail

# ---------- 配置 ----------
APP_NAME="kb-backend"
IMAGE="${KB_IMAGE:-ghcr.io/lang-1234/knowledge-base-backend:latest}"  # ← 改成你的
DATA_DIR="${KB_DATA_DIR:-$HOME/kb-data}"
PORT="${KB_PORT:-8000}"
DOMAIN="${KB_DOMAIN:-}"    # 可选：留空则只开 HTTP
EMAIL="${KB_EMAIL:-}"      # 申请 Let's Encrypt 用

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ---------- 前置检查 ----------
[ "$(id -u)" -ne 0 ] && err "需要 root 权限，请用 sudo 或 root 用户运行"
command -v docker >/dev/null || err "Docker 未安装。请先在应用中心装 Docker。"

# ---------- 准备数据目录 ----------
info "创建数据目录：$DATA_DIR"
mkdir -p "$DATA_DIR"/{sqlite,chroma,logs,ssl,www}

# ---------- 生成 JWT 密钥（首次） ----------
ENV_FILE="$DATA_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  info "生成 .env（首次安装）"
  JWT_SECRET=$(openssl rand -hex 32)
  cat > "$ENV_FILE" <<EOF
# 个人 AI 知识库 - 配置文件
# ⚠️ 不要提交到 Git！本文件含敏感信息

# JWT 签名密钥（64 字符）
JWT_SECRET=$JWT_SECRET

# DeepSeek API（登录后到设置页填更安全，这里只是兜底）
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 通义千问 Embedding（可选）
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3

# ChromaDB 持久化路径（容器内）
CHROMA_PATH=/app/data/chroma
SQLITE_PATH=/app/data/sqlite/kb.db

# 日志级别
LOG_LEVEL=INFO
EOF
  warn "请编辑 $ENV_FILE 填入 API key"
  read -p "现在编辑吗？[y/N] " edit
  if [[ "$edit" =~ ^[Yy]$ ]]; then
    ${EDITOR:-nano} "$ENV_FILE"
  fi
else
  info ".env 已存在，跳过生成"
fi

# ---------- 拉镜像 ----------
info "拉取后端镜像：$IMAGE"
docker pull "$IMAGE" || err "拉镜像失败，请检查网络 / 镜像地址"

# ---------- 停旧容器 ----------
if docker ps -a --format '{{.Names}}' | grep -qx "$APP_NAME"; then
  warn "发现旧容器，先停掉"
  docker rm -f "$APP_NAME" >/dev/null
fi

# ---------- 起容器 ----------
info "启动后端容器"
docker run -d \
  --name "$APP_NAME" \
  --restart unless-stopped \
  -p "${PORT}:8000" \
  -v "$DATA_DIR/sqlite":/app/data/sqlite \
  -v "$DATA_DIR/chroma":/app/data/chroma \
  -v "$DATA_DIR/logs":/app/logs \
  -v "$ENV_FILE":/app/.env:ro \
  -e TZ=Asia/Shanghai \
  --health-cmd "curl -f http://localhost:8000/api/health || exit 1" \
  --health-interval 30s \
  --health-timeout 10s \
  --health-retries 3 \
  "$IMAGE"

# ---------- 等就绪 ----------
info "等待健康检查..."
for i in {1..30}; do
  sleep 2
  if docker inspect --format='{{.State.Health.Status}}' "$APP_NAME" 2>/dev/null | grep -q healthy; then
    info "后端启动成功！"
    break
  fi
  if [ "$i" -eq 30 ]; then
    err "30 秒内未就绪，请 docker logs $APP_NAME 查看"
  fi
done

# ---------- 防火墙 ----------
if command -v ufw >/dev/null; then
  warn "检测到 ufw，开放端口 $PORT"
  ufw allow "$PORT/tcp" 2>/dev/null || true
fi

# ---------- 反代 + HTTPS（可选）----------
if [ -n "$DOMAIN" ] && [ -n "$EMAIL" ]; then
  info "配置 Caddy 反代 + 自动 HTTPS（$DOMAIN）"
  if ! command -v caddy >/dev/null; then
    warn "未检测到 caddy，尝试安装..."
    apt-get update -qq && apt-get install -y -qq caddy 2>/dev/null || \
      curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' 2>/dev/null | apt-key add - 2>/dev/null
  fi
  cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    encode gzip
    reverse_proxy 127.0.0.1:$PORT
    # SSE 流式响应：禁用缓存
    reverse_proxy 127.0.0.1:$PORT {
        flush_interval -1
    }
}
EOF
  systemctl reload caddy 2>/dev/null && info "Caddy 已重载" || warn "Caddy 重载失败，请手动 systemctl reload caddy"
fi

# ---------- 备份 cron ----------
CRON_FILE="/etc/cron.d/kb-backup"
if [ ! -f "$CRON_FILE" ]; then
  info "安装每日自动备份（凌晨 3 点）"
  cat > "$CRON_FILE" <<EOF
# 每日 3 点备份 kb-data 到 kb-data/backups
0 3 * * * root tar -czf $DATA_DIR/backups/kb-\$(date +\%Y\%m\%d).tar.gz -C $DATA_DIR sqlite chroma 2>/dev/null && find $DATA_DIR/backups -mtime +30 -delete
EOF
  mkdir -p "$DATA_DIR/backups"
  info "备份已配置"
fi

# ---------- 完成 ----------
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "NAS-IP")
echo
echo "=========================================="
info "🎉 部署完成！"
echo "  本地访问：http://$LOCAL_IP:$PORT"
[ -n "$DOMAIN" ] && echo "  公网访问：https://$DOMAIN"
echo "  健康检查：http://$LOCAL_IP:$PORT/api/health"
echo
echo "  客户端设置里 API 地址填："
[ -n "$DOMAIN" ] && echo "    https://$DOMAIN" || echo "    http://$LOCAL_IP:$PORT"
echo
echo "  常用命令："
echo "    docker logs -f $APP_NAME      # 看日志"
echo "    docker restart $APP_NAME      # 重启"
echo "    docker stop $APP_NAME         # 停止"
echo "    bash $0                       # 重新跑本脚本（更新用）"
echo "=========================================="
