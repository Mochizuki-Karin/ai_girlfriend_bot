# AI Girlfriend Bot - Makefile

.PHONY: help install start stop restart logs status clean persona knowledge stats

# 默认目标
help:
	@echo "AI Girlfriend Bot - 虚拟女友机器人"
	@echo ""
	@echo "可用命令:"
	@echo "  make install     - 安装依赖"
	@echo "  make start       - 启动服务 (Docker)"
	@echo "  make start-local - 本地运行"
	@echo "  make stop        - 停止服务"
	@echo "  make restart     - 重启服务"
	@echo "  make logs        - 查看日志"
	@echo "  make status      - 查看状态"
	@echo "  make clean       - 清理数据"
	@echo "  make persona     - 编辑人设"
	@echo "  make knowledge   - 导入知识"
	@echo "  make stats       - 查看统计"
	@echo "  make build       - 构建 Docker 镜像"
	@echo "  make shell       - 进入容器"

# 安装依赖
install:
	pip install -r requirements.txt

# Docker 启动
start:
	docker-compose up -d
	@echo "✅ 服务已启动"
	@echo "查看日志: make logs"

# 带 Redis 启动
start-redis:
	docker-compose --profile with-redis up -d
	@echo "✅ 服务已启动（含Redis）"

# 本地启动
start-local:
	python -m src.bot

# 停止服务
stop:
	docker-compose down
	@echo "✅ 服务已停止"

# 重启服务
restart: stop start

# 查看日志
logs:
	docker-compose logs -f --tail=100

# 查看状态
status:
	@echo "📊 容器状态:"
	@docker-compose ps
	@echo ""
	@echo "📊 资源使用:"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 清理数据
clean:
	@echo "⚠️  这将删除所有数据!"
	@read -p "确认? [y/N] " confirm && [ $$confirm = y ] && \
		docker-compose down -v && \
		rm -rf data/* logs/* && \
		echo "✅ 数据已清理" || \
		echo "❌ 已取消"

# 编辑人设
persona:
	python tools/persona_editor.py

# 导入知识
knowledge:
	@echo "知识导入工具"
	@echo "用法: python tools/knowledge_importer.py [file|dir|text|stats] <参数>"

# 查看统计
stats:
	python tools/knowledge_importer.py stats

# 构建镜像
build:
	docker-compose build

# 进入容器
shell:
	docker-compose exec ai-girlfriend-bot /bin/sh

# 更新代码
update:
	git pull
	docker-compose build
	docker-compose up -d

# 备份数据
backup:
	@mkdir -p backups
	@tar -czf backups/backup-$$(date +%Y%m%d-%H%M%S).tar.gz data/ config/
	@echo "✅ 备份完成"

# 恢复数据
restore:
	@ls -t backups/ | head -5
	@read -p "输入备份文件名: " file && \
		tar -xzf backups/$$file && \
		echo "✅ 恢复完成"

# 测试
test:
	pytest tests/ -v

# 代码格式化
format:
	black src/ tools/
	isort src/ tools/

# 代码检查
lint:
	flake8 src/ tools/
	mypy src/

# 完整部署
deploy: build start
	@echo "🚀 部署完成!"
