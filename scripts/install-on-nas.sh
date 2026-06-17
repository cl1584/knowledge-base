#!/usr/bin/env bash
# ==============================================================
# 个人 AI 知识库 - NAS 一键安装脚本
# 适用：飞牛 fnOS / Debian / Ubuntu / 其他 Linux NAS
#
# 用法：
#   sudo bash install-on-nas.sh
#   sudo KB_IMAGE=ghcr.io/你的用户名/knowledge-base-backend:latest bash install-on-nas.sh
#
# 完成后：**在客户端里**完成所有配置（API key、登录账号等）
# ==============================================================
set -euo pipefail

# ---------- 默认配置（用环境变量覆盖）----------
APP_NAME="kb-backend"
IMAGE="${KB_IMAGE:-ghcr.io/cl1584/knowledge-base-backend:latest}"
DATA_DIR="${KB_DATA_DIR:-$HOME/kb-data}"
PORT="${KB_PORT:-8000}"
DOMAIN="${KB_DOMAIN:-}"    # 留空则只开 HTTP，不配 HTTPS
EMAIL="${KB_EMAIL:-}"      # 配 HTTPS 时需要

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }
title() { echo -e "\n${BOLD}${CYAN}== $* ==${NC}"; }

# ---------- 前置检查 ----------
title "检查环境"
[ "$(id -u)" -ne 0 ] && err "需要 root 权限，请用 sudo 或 root 用户运行"
command -v docker >/dev/null || err "Docker 未安装。请先在应用中心装 Docker。"
info "Docker OK"

# ---------- 准备数据目录 ----------
title "准备数据目录"
mkdir -p "$DATA_DIR"/{sqlite,chroma,logs,backups}
info "数据目录：$DATA_DIR"

# ---------- 生成 .env（自动，不卡 nano）----------
ENV_FILE="$DATA_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  info "生成 .env（API key 留空——稍后在客户端里填）"
  JWT_SECRET=$(openssl rand -hex 32)
  cat > "$ENV_FILE" <<EOF
# 个人 AI 知识库 - 配置文件
# ⚠️ 含敏感信息，禁止 commit

# JWT 签名密钥（自动生成）
JWT_SECRET=$JWT_SECRET

# DeepSeek（留空——客户端设置页填）
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

LOG_LEVEL=INFO
EOF
  chmod 600 "$ENV_FILE"
  info ".env 已生成（$ENV_FILE）"
else
  info ".env 已存在，跳过"
fi

# ---------- 拉镜像 ----------
title "拉取后端镜像"
echo "  镜像：$IMAGE"
docker pull "$IMAGE" || err "拉镜像失败"

# ---------- 停旧容器 ----------
if docker ps -a --format '{{.Names}}' | grep -qx "$APP_NAME"; then
  warn "停掉旧容器 $APP_NAME"
  docker rm -f "$APP_NAME" >/dev/null
fi

# ---------- 起容器 ----------
title "启动后端"
# ⚠️ 用 on-failure:5 替代 unless-stopped：
#   - 容器连续崩 5 次后停止自动重启（避免 fast-fail 循环浪费 CPU）
#   - 调试阶段你看到容器 exited 是干净的信号，不会一直被 docker 自动拉起
#   - 修复 bug 后手动 docker start $APP_NAME 即可恢复
docker run -d \
  --name "$APP_NAME" \
  --restart on-failure:5 \
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
  "$IMAGE" >/dev/null
info "容器已启动（自动重启最多 5 次后停止）"

# ---------- 等就绪 ----------
title "等待健康检查"
for i in $(seq 1 30); do
  sleep 2
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$APP_NAME" 2>/dev/null || echo "starting")
  [ "$STATUS" = "healthy" ] && { info "后端就绪（${i}x2s）"; break; }
  # 容器如果已 exited（说明崩了），立刻跳出而不是傻等 30s
  RUNNING=$(docker inspect --format='{{.State.Running}}' "$APP_NAME" 2>/dev/null || echo "false")
  if [ "$RUNNING" != "true" ]; then
    err "容器已退出，请运行：docker logs $APP_NAME"
  fi
  [ "$i" -eq 30 ] && err "30 秒内未就绪，docker logs $APP_NAME"
done

# ---------- 防火墙 ----------
if command -v ufw >/dev/null; then
  ufw allow "$PORT/tcp" 2>/dev/null || true
  info "ufw 已放行 $PORT"
fi

# ---------- 可选：Caddy HTTPS ----------
if [ -n "$DOMAIN" ] && [ -n "$EMAIL" ]; then
  title "配置 HTTPS（$DOMAIN）"
  if ! command -v caddy >/dev/null; then
    warn "安装 caddy..."
    apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq caddy 2>/dev/null || \
      curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' 2>/dev/null | apt-key add - 2>/dev/null || true
  fi
  cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    encode gzip
    reverse_proxy 127.0.0.1:$PORT {
        flush_interval -1
    }
}
EOF
  systemctl reload caddy 2>/dev/null && info "Caddy 已重载" || warn "请手动: systemctl reload caddy"
fi

# ---------- 备份 cron ----------
CRON_FILE="/etc/cron.d/kb-backup"
if [ ! -f "$CRON_FILE" ]; then
  title "配置每日自动备份"
  cat > "$CRON_FILE" <<EOF
# 每日 3 点备份 kb-data
0 3 * * * root tar -czf $DATA_DIR/backups/kb-\$(date +\%Y\%m\%d).tar.gz -C $DATA_DIR sqlite chroma 2>/dev/null && find $DATA_DIR/backups -mtime +30 -delete
EOF
  info "每日 3 点自动备份"
fi

# ---------- 完成 ----------
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$LOCAL_IP" ] && LOCAL_IP="NAS-IP"

API_URL=$([ -n "$DOMAIN" ] && echo "https://$DOMAIN" || echo "http://$LOCAL_IP:$PORT")

cat <<EOF

${BOLD}${GREEN}========================================${NC}
${BOLD}${GREEN}  🎉 部署完成！${NC}
${BOLD}${GREEN}========================================${NC}

${BOLD}1. 在电脑上装客户端${NC}
   - 打开 GitHub 仓库：https://github.com/cl1584/knowledge-base/releases
   - 下载最新 ${BOLD}知识库_0.x.x_x64-setup.exe${NC}（1.7 MB）
   - 双击安装

${BOLD}2. 启动客户端 + 注册账号${NC}
   - 打开「知识库」
   - 登录页点「注册」→ 填邮箱密码
   - 登录成功

${BOLD}3. 在客户端里配置 API 地址${NC}
   - 右上角 ⚙️ → 「设置」
   - API 地址填：${CYAN}${API_URL}${NC}
   - 保存

${BOLD}4. 配置 AI 模型（可选，但需要它才能对话）${NC}
   - 还在设置页
   - 选「DeepSeek」（或其他）
   - 填你的 API key → 保存
   - 立即可用，${BOLD}不需要回到 NAS 改任何东西${NC}

${BOLD}其他：${NC}
   - 健康检查：${API_URL}/api/health
   - NAS 端查日志：docker logs -f $APP_NAME
   - 查最近 30 行：docker logs --tail 30 $APP_NAME
   - 重启后端：   docker restart $APP_NAME
   - 重新拉镜像： sudo bash install-on-nas.sh（脚本会自停旧起新）
   - 调试技巧：  容器退出后 \`docker start $APP_NAME\` 不会自动重启（因为 on-failure:5 限 5 次）
                想改回无限重启：\${NC}docker update --restart unless-stopped $APP_NAME\${BOLD}

${BOLD}NAS 已就绪，全部操作都在客户端里完成 ✨${NC}

EOF
