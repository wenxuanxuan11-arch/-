# 皖江工学院校园小猫户口收录系统

## 启动

```powershell
docker compose up -d --build
```

启动后访问：

```text
http://localhost:8080
```

同一局域网内的其他设备可以通过本机局域网 IP 访问，例如：

```text
http://192.168.1.10:8080
```

## 管理员身份

管理员学号、姓名和端口在 `.env` 中配置。修改后执行：

```powershell
docker compose up -d
```

普通用户使用任意有效学号和姓名登录，只能查看档案。管理员使用 `.env` 中完全一致的学号和姓名登录，可以新增、编辑、删除、导入档案，并查看访问统计。

## 数据

档案、访问人员、访问日志和登录会话保存在 `data/registry.db`。备份网站数据时，备份整个 `data` 文件夹即可。

## 推到 GitHub 后部署

本项目包含后端和 SQLite 数据库，不能完整部署到 GitHub Pages。请把仓库连接到 Render、Railway 或 Fly.io 这类可以运行 Docker 的平台。部署说明见：

```text
DEPLOYMENT.md
```

Render 一键接入：

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fwenxuanxuan11-arch%2F-.git)

仓库里已经准备了：

```text
Dockerfile        线上云平台使用
Dockerfile.local  本机 Docker Compose 使用
render.yaml       Render 部署入口
railway.json      Railway 部署入口
fly.toml          Fly.io 部署入口
```

## 常用命令

```powershell
docker compose ps
docker compose logs -f
docker compose restart
docker compose down
```
