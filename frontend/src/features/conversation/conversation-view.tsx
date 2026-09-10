import { useState } from "react";
import {
  ArrowUp,
  Check,
  CircleDashed,
  CircleAlert,
  FileText,
  LoaderCircle,
  RotateCcw,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { Raw } from "../../components/evidence/common";
import { summarizeOutput } from "../../components/evidence/run-track";
import { Button } from "../../components/ui/button";
import type { SessionConversation, AgentRunRow } from "../runtime/projection";

const STATUS_ICON: Record<
  AgentRunRow["status"],
  { icon: typeof Check; label: string; tone: string }
> = {
  queued: { icon: CircleDashed, label: "排队", tone: "queued" },
  running: { icon: LoaderCircle, label: "执行中", tone: "running" },
  completed: { icon: Check, label: "已完成", tone: "completed" },
  failed: { icon: CircleAlert, label: "失败", tone: "failed" },
  cancelled: { icon: CircleAlert, label: "已取消", tone: "failed" },
  timed_out: { icon: CircleAlert, label: "已超时", tone: "failed" },
};

function AgentProcess({ agent }: { agent: AgentRunRow }) {
  return (
    <div className="agent-process">
      {agent.messages.map((m) => (
        <div className="agent-process-item" key={`${m.from}-${m.to}-${m.sourceEventIds[0] ?? ""}`}>
          <span className="process-verb">输入</span>
          <span>
            {m.from ?? "原始任务"} → {agent.nodeId}
            {m.sourceEventIds.length > 0 && (
              <small> 来源 {m.sourceEventIds.join("、")}</small>
            )}
          </span>
        </div>
      ))}
      <div className="agent-process-item">
        <span className="process-verb">产物</span>
        <span>
          {agent.output !== null && agent.output !== undefined
            ? "已保存结构化产物（见下方展开）"
            : "未提供产物"}
        </span>
      </div>
      {agent.output !== null && agent.output !== undefined && (
        <Raw value={agent.output} title="展开结构化输出" />
      )}
      <p className="tiny">
        实例 {agent.instanceId}
        {agent.startedAt && ` · 开始于 ${agent.startedAt.slice(11, 19)}`}
        {agent.endedAt && ` · 结束于 ${agent.endedAt.slice(11, 19)}`}
        。完整过程见"轨迹"视图。
      </p>
    </div>
  );
}

function AgentRow({ agent }: { agent: AgentRunRow }) {
  const [open, setOpen] = useState(false);
  const status = STATUS_ICON[agent.status];
  const Icon = status.icon;
  const step = summarizeOutput(agent.output) ?? agent.step ?? "等待上游";
  return (
    <div className={`agent-row ${status.tone}`}>
      <button
        type="button"
        className="agent-row-head"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span className="agent-mark">◇</span>
        <span className="agent-name">{agent.nodeId}</span>
        <span className="agent-step">{step}</span>
        <span className={`agent-status ${status.tone}`}>
          <Icon size={12} className={agent.status === "running" ? "spin" : ""} />
          {status.label}
        </span>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
      </button>
      {open && <AgentProcess agent={agent} />}
    </div>
  );
}

export function Composer() {
  return (
    <div className="composer" aria-label="任务输入">
      <textarea
        rows={1}
        disabled
        placeholder="输入任务，或继续当前任务……"
        aria-label="任务输入（暂未开放）"
      />
      <div className="composer-bar">
        <span className="tiny">
          实时提交依赖执行作业服务（契约 F1/F2）。当前会话为只读回放，运行中不支持插入指令。
        </span>
        <Button size="icon" disabled aria-label="发送">
          <ArrowUp size={15} />
        </Button>
      </div>
    </div>
  );
}

export function ConversationView({
  conversation,
  onOpenArtifact,
}: {
  conversation: SessionConversation;
  onOpenArtifact: () => void;
}) {
  const [folded, setFolded] = useState(true);
  const plan = conversation.plan;
  const scheduleCount = plan?.schedule.length ?? 0;
  return (
    <div className="transcript">
      {conversation.instruction ? (
        <div className="chat-user">
          <span className="chat-who">User</span>
          <p>{conversation.instruction}</p>
        </div>
      ) : (
        <div className="chat-user">
          <span className="chat-who">User</span>
          <p className="tiny">该记录未提供任务说明。</p>
        </div>
      )}

      {folded && conversation.counts.agents > 0 ? (
        <button
          type="button"
          className="fold-bar"
          aria-expanded={!folded}
          onClick={() => setFolded(false)}
        >
          {conversation.counts.agents} 个 Agent ·{" "}
          {conversation.counts.messages} 条协作消息 ·{" "}
          {conversation.counts.artifacts} 个产物
          <ChevronRight size={13} />
        </button>
      ) : (
        conversation.agents.length > 0 && (
          <div className="agent-rows">
            {conversation.agents.map((agent) => (
              <AgentRow key={agent.agentRunId} agent={agent} />
            ))}
            <button
              type="button"
              className="fold-bar collapsed"
              aria-expanded={true}
              onClick={() => setFolded(true)}
            >
              收起执行过程
              <ChevronDown size={13} />
            </button>
          </div>
        )
      )}

      {plan && (
        <div className="chat-artifact">
          <span className="chat-who">EvoTeam</span>
          <div className="artifact-card">
            <FileText size={15} />
            <div>
              <strong>项目计划</strong>
              <small>
                排期 {scheduleCount} 项工作 · 风险 {plan.risks.length} 条 · 校验依据{" "}
                {plan.validation_notes.length} 条
              </small>
            </div>
            <Button variant="outline" onClick={onOpenArtifact}>
              在产物面板打开
            </Button>
          </div>
        </div>
      )}

      <div className="chat-system">
        <span className="chat-who">系统</span>
        <p className="tiny">
          {conversation.evaluation?.metrics.success === true
            ? "独立评价：规则检查通过"
            : conversation.evaluation?.metrics.success === false
              ? `独立评价：规则检查未通过（${conversation.evaluation.metrics.hard_constraint_errors ?? "未知"} 个硬约束错误）`
              : "独立评价结果未提供"}
          {conversation.terminationReason && ` · 终止原因：${conversation.terminationReason}`}
          {" · "}
          封存于 {conversation.sealedAt.slice(0, 19).replace("T", " ")}
        </p>
      </div>
    </div>
  );
}

export function RetryHint() {
  return (
    <p className="tiny retry-hint">
      <RotateCcw size={11} /> 运行中用户输入仅作为展示层注记，不参与本次执行；该能力随实时执行服务交付。
    </p>
  );
}
