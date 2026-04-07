## 1. 配置迁移

- [ ] 1.1 修改 `src/hot_pulse/config.py`：在 `SecretConfig` 中新增 `feishu_bitable_app_token`、`feishu_bitable_table_id`、`dingtalk_webhook_url` 字段
- [ ] 1.2 修改 `src/hot_pulse/config.py`：在 `load_config()` 中添加 secrets 值覆盖 YAML 配置的逻辑
- [ ] 1.3 修改 `config.yaml`：将 `app_token`、`table_id`、`webhook_url` 值清空为占位符
- [ ] 1.4 修改 `.env.example`：添加新增环境变量条目及注释
- [ ] 1.5 创建 `config.yaml.example`：不含真实凭证的模板文件

## 2. 清理

- [ ] 2.1 确认 `.gitignore` 中包含 `config.yaml` 和 `.env`
- [ ] 2.2 评估并处理 git 历史中的敏感信息（可选：重建仓库或使用 BFG 清理）

## 3. 验证

- [ ] 3.1 确认 load_config() 正确合并 .env 凭证和 YAML 非敏感配置
