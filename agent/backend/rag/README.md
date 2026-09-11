# 第 41 课模型重排接入

FAQ 与促销路径现在在混合召回后调用配置的 `/rerank` 服务，默认模型为
`Qwen/Qwen3-Reranker-8B`。重排将问题与每条候选政策配对打分，并按模型分数排序。
无需安装本地模型，使用现有 httpx 依赖。

## 配置

沿用 `.env`：

```dotenv
AGENT_RAG_RERANK_ENABLED=true
AGENT_RAG_RERANK_MODEL=Qwen/Qwen3-Reranker-8B
AGENT_RAG_RERANK_BASE_URL=https://api.siliconflow.cn/v1
AGENT_RAG_RERANK_TIMEOUT_SECONDS=15
AGENT_RAG_RERANK_MIN_SCORE=0.5
```

同一提供商默认复用 `AGENT_OPENAI_API_KEY`。跨提供商时必须配置独立的
`AGENT_RAG_RERANK_API_KEY`，不会把聊天密钥自动发送到另一个主机。修改配置后重启后端。
API 契约：https://docs.siliconflow.cn/docs/api/rerank-post

## 行为

- 保留所有达到阈值的受信候选，允许同一知识域内多问题引用多份政策。
- 不使用“出现叠加但不足两条政策就清空”的旧规则；一条相关政策也可以回答。
- 模型重排成功后不按政策 ID 复用最终答案，最终模型根据当前问题和证据组织回答。
- 证据均低于阈值时走原有低置信度兜底，不退回高分的原始相似度冒充可信证据。
- 超时、HTTP 错误、响应索引重复/缺失/越界、分数非法等情况保留旧路径，并记录明确回退原因。
- 关闭重排恢复旧 FAQ/促销路径。关闭开关不等于关闭向量检索或聊天模型。
- 显式未发布政策拦截、知识域约束、业务权限、退款/退货工作流保持原有行为。

`rag_model_reranked` Trace 记录模型名、是否实际使用模型、原始与重排顺序、分数、
选中/排除的政策、耗时和回退原因。原始召回分数保留在 Citation metadata 的
`retrieval_score`，不能与 rerank_score 混为同一种度量。
提供商返回的 token 用量记录在该事件的 `usage`，尚未计入原有聊天 `cost_summary`。

## 限制与验证

0.5 是初始可配置相关性阈值，未做独立数据集校准，不代表 50% 的答对概率。
重排不会增加召回池之外的资料，跨知识域多意图仍受原路由限制。
这次同时调整了证据保留和 FAQ 缓存使用方式，最终回答变化不能全部归因于重排模型。
模型请求失败时回到旧逻辑，旧路径的已知不足仍可能出现，Trace 会注明降级。

从 backend 目录运行：

```powershell
& '../../../.venv/Scripts/python.exe' -m unittest discover -s tests -p test_model_reranker.py -v
```

本机原版保存在 `.runtime/original-project`。新增运行副本位于 `.runtime/rerank-project`，
以原版为基础，仅接入本次 RAG 变更；主源码中的同样改动与此前售后状态修复共存。
用仓库根目录 `.runtime/start_rerank.ps1 -Port 8000 -Replace` 启动新增版本；
加 `-Version original-project` 切回保留原版。脚本会检查占用进程归属后才替换。
