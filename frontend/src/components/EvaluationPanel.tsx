import type { AgentCapabilityManifest, EvalCaseResult, EvalRunResponse, FeedbackSubmitResponse } from "../types/api";

type EvaluationPanelProps = {
  report?: EvalRunResponse;
  error?: string;
  feedbackReport?: FeedbackSubmitResponse;
  feedbackError?: string;
  isEvaluating: boolean;
  isSubmittingFeedback: boolean;
  capabilities: AgentCapabilityManifest;
  onRunEval: () => Promise<void>;
  onSubmitFeedback: () => Promise<void>;
};

export function EvaluationPanel({
  report,
  error,
  feedbackReport,
  feedbackError,
  isEvaluating,
  isSubmittingFeedback,
  capabilities,
  onRunEval,
  onSubmitFeedback,
}: EvaluationPanelProps) {
  const failedCases = report?.results.filter((result) => !result.passed).slice(0, 4) ?? [];
  const failureCounts = report ? countFailureCategories(report.results) : {};
  const scenarioCounts = report ? countScenarioCoverage(report.results) : {};
  const passRate = report?.total ? `${Math.round((report.passed / report.total) * 100)}%` : undefined;
  const evaluationAvailable = capabilities.endpoints?.eval_run !== false && capabilities.features?.evaluation !== false;
  const feedbackAvailable = capabilities.features?.feedback_submit === true;
  const primaryAttribution = feedbackReport?.record.attributions[0];

  return (
    <section className="panel evaluation-panel" aria-label="Evaluation 回归评测">
      <div className="panel-header evaluation-header">
        <div>
          <span>Evaluation 回归评测</span>
          <small>独立运行固定 case，验证核心客服场景有没有退化。</small>
        </div>
        <button className="inline-action" type="button" disabled={isEvaluating || !evaluationAvailable} onClick={onRunEval}>
          {isEvaluating ? "运行中..." : evaluationAvailable ? "运行评测" : "当前版本未开放"}
        </button>
      </div>

      <div className="evaluation-grid">
        <div className="trace-card evaluation-summary">
          <strong>回归门禁</strong>
          {isEvaluating ? <span className="evaluation-status">正在运行评测用例，可能需要几十秒。</span> : null}
          {!evaluationAvailable ? (
            <span className="evaluation-status">
              {capabilities.disabled_reasons?.evaluation || "目标 Agent 的能力配置中没有开放 Evaluation。"}
            </span>
          ) : null}
          {error ? <span className="evaluation-error">{error}</span> : null}
          {report ? (
            <>
              <div className="metric-grid compact">
                <Metric label="总数" value={numberValue(report.total)} />
                <Metric label="通过" value={numberValue(report.passed)} />
                <Metric label="失败" value={numberValue(report.failed)} />
                <Metric label="通过率" value={passRate} />
              </div>
              <MetaList
                items={[
                  ["schema", stringValue(report.summary.schema_version)],
                  ["边界", stringValue(report.summary.boundary)],
                ]}
              />
            </>
          ) : (
            <span>用于观察固定 case 的通过数、失败类别和缺失信号；不是线上监控、人工质检或 LLM-as-judge。</span>
          )}
        </div>

        <div className="evaluation-focus">
          <FocusCard title="路径正确性" body="看 Tool、RAG citation、trace event 和 session_state，不只看最终回答。" />
          <FocusCard title="风险边界" body="检查 forbidden tool、敏感文本泄露、Prompt 注入和审批绕过。" />
          <FocusCard title="回归定位" body="失败类别要能指向 Tool、RAG、Trace、Context 或安全层。" />
          <FocusCard title="上线边界" body="离线 eval 是上线前门禁，线上还需要监控、抽检和 A/B。" />
        </div>
      </div>

      <div className="evaluation-detail-grid">
        <div className="trace-card">
          <strong>面试关注的校验维度</strong>
          <div className="metric-grid eval-dimension-grid">
            <Metric label="工具路径" value={report ? numberValue(failureCounts.tool_path_mismatch ?? 0) : "expected / forbidden"} />
            <Metric label="RAG 引用" value={report ? numberValue(failureCounts.citation_missing ?? 0) : "citation"} />
            <Metric label="Trace 信号" value={report ? numberValue(failureCounts.trace_event_missing ?? 0) : "event"} />
            <Metric label="状态边界" value={report ? numberValue(failureCounts.session_state_mismatch ?? 0) : "session_state"} />
            <Metric label="安全禁用" value={report ? numberValue(failureCounts.forbidden_text_present ?? 0) : "forbidden text"} />
            <Metric label="回答信号" value={report ? numberValue(failureCounts.answer_signal_missing ?? 0) : "keyword"} />
          </div>
          <small>{report ? "数字表示该维度当前失败 case 数；0 代表本次没有发现对应退化。" : "这些维度来自课程里的面试题：证明 Agent 没退化，要同时验证答案和中间路径。"}</small>
        </div>

        <div className="trace-card">
          <strong>核心场景覆盖</strong>
          <div className="metric-grid eval-dimension-grid">
            <Metric label="物流/订单" value={report ? numberValue(scenarioCounts.order ?? 0) : "Tool"} />
            <Metric label="FAQ/RAG" value={report ? numberValue(scenarioCounts.rag ?? 0) : "Citation"} />
            <Metric label="商品推荐" value={report ? numberValue(scenarioCounts.product ?? 0) : "Tool + RAG"} />
            <Metric label="售后边界" value={report ? numberValue(scenarioCounts.afterSale ?? 0) : "Workflow"} />
            <Metric label="Memory" value={report ? numberValue(scenarioCounts.memory ?? 0) : "Context"} />
            <Metric label="安全注入" value={report ? numberValue(scenarioCounts.security ?? 0) : "Guardrail"} />
          </div>
          <small>{report ? "数字表示本次评测覆盖到的 case 数。" : "覆盖面要能回答面试官追问：改 Prompt、Tool、RAG 或 Memory 后，哪些关键业务路径会被回归验证。"}</small>
        </div>
      </div>

      <div className="trace-card evaluation-playbook">
        <strong>失败后怎么定位</strong>
        <div className="playbook-grid">
          <span>missing tool：回看 Tool schema、description、routing 和 clarification</span>
          <span>missing citation：回看 RAG router、知识库、query rewrite 和 retrieval_stage</span>
          <span>trace/session_state 缺失：回看 Workflow、HITL、Hooks 和 ContextBuilder</span>
          <span>forbidden text/tool：回看 Prompt 安全、Runtime Context 和高风险边界</span>
        </div>
      </div>

      {feedbackAvailable ? (
        <div className="trace-card evaluation-playbook">
          <div className="card-title-row">
            <strong>反馈归因与回填</strong>
            <button className="inline-action" type="button" disabled={isSubmittingFeedback} onClick={onSubmitFeedback}>
              {isSubmittingFeedback ? "提交中..." : "提交示例反馈"}
            </button>
          </div>
          {feedbackError ? <span className="evaluation-error">{feedbackError}</span> : null}
          {feedbackReport ? (
            <>
              <MetaList
                items={[
                  ["feedback", feedbackReport.record.feedback_id],
                  ["绑定 case", feedbackReport.record.case_id],
                  ["trace 事件", listValue(feedbackReport.record.trace_event_names)],
                  ["Eval 失败类别", listValue(feedbackReport.record.eval_failure_categories)],
                  ["归因模块", primaryAttribution?.module],
                  ["归因类型", primaryAttribution?.category],
                  ["回填 case", stringValue(feedbackReport.record.backfilled_case.case_id)],
                ]}
              />
              <span>{primaryAttribution?.suggested_fix}</span>
            </>
          ) : (
            <span>把用户差评绑定到当前会话 trace 和固定 eval case，再归因到具体模块并回填一个新 case。</span>
          )}
        </div>
      ) : null}

      <div className="evaluation-failures">
        {failedCases.length ? (
          failedCases.map((result) => (
            <div className="trace-card" key={result.case_id}>
              <strong>{result.case_id}</strong>
              <span>{result.user_message}</span>
              <MetaList
                items={[
                  ["失败类别", listValue(result.failure_categories)],
                  ["缺失信号", listValue(result.missing_signals)],
                  ["缺失工具", listValue(result.missing_tools)],
                  ["禁止工具", listValue(result.unexpected_tools)],
                  ["缺失引用", listValue(result.missing_citations)],
                  ["缺失 trace", listValue(result.missing_trace_events)],
                  ["状态缺失", listValue(result.missing_session_state)],
                  ["敏感命中", listValue(result.forbidden_text_hits)],
                ]}
              />
            </div>
          ))
        ) : (
          <div className="trace-card muted">{report ? "当前没有失败 case。" : "运行评测后，这里展示失败 case、失败类别和缺失信号。"}</div>
        )}
      </div>
    </section>
  );
}

function FocusCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="evaluation-focus-card">
      <strong>{title}</strong>
      <span>{body}</span>
    </div>
  );
}

function countFailureCategories(results: EvalCaseResult[]) {
  return results.reduce<Record<string, number>>((counts, result) => {
    (result.failure_categories ?? []).forEach((category) => {
      counts[category] = (counts[category] ?? 0) + 1;
    });
    return counts;
  }, {});
}

function countScenarioCoverage(results: EvalCaseResult[]) {
  return results.reduce<Record<string, number>>((counts, result) => {
    const id = result.case_id;
    if (id.includes("order") || id.includes("logistics")) {
      counts.order = (counts.order ?? 0) + 1;
    }
    if (id.includes("faq") || id.includes("rag") || (result.actual_citations ?? []).length) {
      counts.rag = (counts.rag ?? 0) + 1;
    }
    if (id.includes("product") || id.includes("promotion")) {
      counts.product = (counts.product ?? 0) + 1;
    }
    if (id.includes("refund") || id.includes("return") || id.includes("approval")) {
      counts.afterSale = (counts.afterSale ?? 0) + 1;
    }
    if (id.includes("preference") || id.includes("memory") || id.includes("context")) {
      counts.memory = (counts.memory ?? 0) + 1;
    }
    if (id.includes("prompt-injection") || (result.forbidden_text_hits ?? []).length || (result.unexpected_tools ?? []).length) {
      counts.security = (counts.security ?? 0) + 1;
    }
    return counts;
  }, {});
}

function Metric({ label, value }: { label: string; value?: string }) {
  return (
    <div className="metric-card">
      <small>{label}</small>
      <strong>{value || "-"}</strong>
    </div>
  );
}

function MetaList({ items }: { items: Array<[string, unknown]> }) {
  const visibleItems = items.filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (!visibleItems.length) {
    return null;
  }

  return (
    <dl className="meta-list">
      {visibleItems.map(([label, value]) => (
        <div key={`${label}-${String(value)}`}>
          <dt>{label}</dt>
          <dd>{String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function numberValue(value?: number) {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : undefined;
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function listValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length ? value.join(" / ") : undefined;
  }
  return stringValue(value);
}
