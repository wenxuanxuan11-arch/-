# GitHub 与线上部署

这个项目需要后端服务和 SQLite 数据库，不能只放到 GitHub Pages。推荐流程是：

1. 把本项目推到 GitHub 仓库。
2. 在 Render、Railway 或 Fly.io 中从 GitHub 仓库部署 Docker 服务。
3. 配置环境变量：

```text
ADMIN_STUDENT_ID=240520230
ADMIN_NAME=宣文轩
SESSION_DAYS=7
DATA_DIR=/data
```

## Render

仓库内已提供 `render.yaml`。在 Render 创建 Blueprint 或 Web Service，连接 GitHub 仓库后使用 Docker 部署。

一键接入链接：

```text
https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fwenxuanxuan11-arch%2F-.git
```

需要注意：SQLite 数据库必须挂载持久磁盘到 `/data`，否则服务重启后数据会丢失。Render 的免费 Web Service 不支持持久磁盘；如果要长期保存档案、访问人员和访问日志，需要选择支持 Persistent Disk 的付费实例。只做演示可以先不挂持久磁盘，但每次重启或重新部署后数据可能重置。

## Railway

仓库内已提供 `railway.json`，Railway 会使用 `Dockerfile` 构建。

需要在 Railway 项目中添加 Volume，并把挂载路径设为 `/data`。同时在 Variables 中填写管理员环境变量。

## Fly.io

仓库内已提供 `fly.toml`。首次部署前需要：

```powershell
fly launch
fly volumes create wanjiang_cat_data --size 1 --region hkg
fly secrets set ADMIN_STUDENT_ID=240520230 ADMIN_NAME=宣文轩
fly deploy
```

## 本机 Docker

本机部署继续使用 `docker-compose.yml` 和 `Dockerfile.local`，因为当前电脑已经有可复用的 Alpine 镜像，适合离线/弱网络环境。

```powershell
docker compose up -d --build
```

本机访问地址默认为：

```text
http://localhost:8090
```
