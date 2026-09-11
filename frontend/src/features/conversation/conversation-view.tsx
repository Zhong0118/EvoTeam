/* Conversation view — V3 §9. Chat is the page itself: no dashboard Panel
   wrapper. Three densities: fold summary > agent rows > raw tool detail,
   with each AgentRow expandable into its own child process. */
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Diamond,
  FileText,
  Search,
  Wrench,
} from "lucide-react";
import { flowKey } from "../runtime/types";
import { projectConversation, type ChatAgentRow } from "../runtime/projections";
import { locateFlowElement, registerFlowElement } from "../runtime/flow-registry";
import { useLiveSession } from "../session/use-live-session";
import { Composer } from "./composer";

function useFlowRef<T extends HTMLElement>(key: string | null) {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || !key) return;
    return registerFlowElement(key, el);
  }, [key]);
  return ref;
}

const statusIcon = (status: ChatAgentRow["status"]) => {
  switch (status) {
    case "running":
      return <span className="ws-status-dot pulse" style={{ color: "var(--primary)" }} aria-label="执行中" />;
    case "completed":
      return <span aria-label="已完成" style={{ color: "#387d66" }}>✓</span>;
    case "failed":
      return <span aria-label="失败" style={{ color: "#a14e45" }}>!</span>;
    default:
      return <span className="ws-status-dot" style={{ color: "var(--muted)", opacity: 0.5 }} aria-label="排队" />;
  }
};

const duration = (ms?: number) =>
  ms == null ? "" : `${(ms / 1000).toFixed(1)}s`;

function ToolRow({
  callId,
  label,
  summary,
  done,
}: {
  callId?: string;
  label: string;
  summary?: string;
  done: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useFlowRef<HTMLButtonElement>(callId ? flowKey.tool(callId) : null);
  return (
    <div className="ws-tool-block">
      <button
        ref={ref}
        className="ws-tool-row"
        onClick={() => {
          setOpen(!open);
          // Graph locate must work from the Chat side too: same tool: key.
          if (callId) locateFlowElement(flowKey.tool(callId));
        }}
        aria-expanded={open}
      >
        {label.startsWith("check") || label.includes("constraint") ? (
          <Search size={13} />
        ) : (
          <Wrench size={13} />
        )}
        <span className="ws-tool-name">{label}</span>
        <span className="ws-tool-summary">{summary}</span>
        <span className="ws-tool-state">
          {done ? "✓" : <span className="ws-status-dot pulse" style={{ color: "var(--primary)" }} />}
        </span>
      </button>
      {open && (
        <div className="ws-tool-detail">
          <div><span className="muted">args</span> {label}(...)</div>
          {summary && <div><span className="muted">result</span> {summary}</div>}
        </div>
      )}
    </div>
  );
}

function AgentRow({ row }: { row: ChatAgentRow }) {
  const [open, setOpen] = useState(false);
  const key = flowKey.agentRun(row.agentRunId);
  const ref = useFlowRef<HTMLDivElement>(key);
  const artifacts = row.steps.filter((s) => s.kind === "artifact").length;
  return (
    <div className="ws-agent-block" ref={ref}>
      <button
        className="ws-agent-row"
        onClick={() => {
          setOpen(!open);
          // V3 §11.7: clicking the Chat row locates (+ flashes) the same
          // AgentRun node in the Live Execution Graph.
          if (!open) locateFlowElement(key);
        }}
        aria-expanded={open}
      >
        <Diamond size={12} className="ws-agent-glyph" />
        <span className="ws-agent-role">
          {row.role}
          {row.agentRunId.endsWith("executor-2") ? " · 返工" : ""}
        </span>
        <span className="ws-agent-action">{row.step || row.title}</span>
        <span className="ws-agent-state">
          {duration(row.durationMs) && <span className="tiny">{duration(row.durationMs)}</span>}
          {statusIcon(row.status)}
          <ChevronRight
            size={13}
            style={{ transform: open ? "rotate(90deg)" : undefined, transition: "transform 150ms" }}
          />
        </span>
      </button>
      {open && (
        <div className="ws-agent-process">
          {row.steps.map((step, i) =>
            step.kind === "tool" ? (
              <ToolRow
                key={step.eventId ?? i}
                callId={step.callId}
                label={step.label}
                summary={step.summary}
                done={step.done}
              />
            ) : step.kind === "artifact" ? (
              <div className="ws-artifact-row" key={step.eventId ?? i}>
                <FileText size={13} /> <span>{step.summary}</span>
              </div>
            ) : (
              <div className="ws-step-row" key={step.eventId ?? i}>
                <span className="ws-step-kind">
                  {step.kind === "thinking" ? "思考" : step.kind === "retry" ? "返工" : "输出"}
                </span>
                <span>{step.summary}</span>
              </div>
            ),
          )}
          <div className="ws-agent-foot tiny">
            {row.toolCalls} tools
            {row.tokens != null && <> · {(row.tokens / 1000).toFixed(1)}k tokens</>}
            {artifacts > 0 && <> · {artifacts} artifacts</>}
          </div>
        </div>
      )}
    </div>
  );
}

export function ConversationView({
  userMessage,
  scriptedUserTask,
  onSubmit,
}: {
  userMessage: string | null;
  scriptedUserTask: string | null;
  onSubmit: (text: string) => void;
}) {
  const { events, running, stop } = useLiveSession();
  const conversation = useMemo(() => projectConversation(events), [events]);
  const [foldOpen, setFoldOpen] = useState(true);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  useEffect(() => {
    const el = transcriptRef.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [events, userMessage]);

  const hasProcess = conversation.agents.length > 0;
  const bubble = userMessage ?? scriptedUserTask;
  const foldLabel = `${conversation.counts.agents} Agents · ${conversation.counts.tools} tools · ${conversation.counts.messages} handoffs · ${conversation.counts.artifacts} artifacts`;

  return (
    <div className="ws-view">
      <div
        className="ws-transcript"
        ref={transcriptRef}
        onScroll={(e) => {
          const el = e.currentTarget;
          stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
        }}
      >
        <div className={`ws-conversation ${bubble || conversation.running ? "has-turn" : "ws-empty-chat"}`}>
          {!bubble && !hasProcess ? (
            <>
              <div className="ws-empty-mark">
                <Diamond size={22} />
              </div>
              <h2 className="ws-empty-title">今天想完成什么？</h2>
              <p className="ws-empty-sub">EvoTeam 会组织一支 Agent 团队执行任务，全过程可追踪</p>
              <div className="ws-empty-hints">
                <button className="ws-hint-chip" onClick={() => onSubmit("为下季度产品发布生成排期并校验资源冲突")}>
                  项目计划
                </button>
                <button className="ws-hint-chip" onClick={() => onSubmit("生成一份可复现的调研报告")}>
                  调研
                </button>
                <button className="ws-hint-chip" onClick={() => onSubmit("分析这份实验数据并输出图表")}>
                  分析
                </button>
              </div>
            </>
          ) : (
            <>
              {bubble && (
                <div className="ws-user-row">
                  <div className="ws-user-bubble">{bubble}</div>
                </div>
              )}
              {hasProcess && !conversation.running && (
                <button className="ws-fold-head" onClick={() => setFoldOpen(!foldOpen)} aria-expanded={foldOpen}>
                  <span className="ws-fold-check">✓ 已完成</span>
                  <span className="ws-fold-stats">{foldLabel}</span>
                  <ChevronDown size={14} style={{ transform: foldOpen ? undefined : "rotate(-90deg)" }} />
                </button>
              )}
              {(conversation.running || foldOpen) && hasProcess && (
                <div className="ws-agent-list">
                  {conversation.agents.map((row) => (
                    <AgentRow key={row.agentRunId} row={row} />
                  ))}
                </div>
              )}
              {conversation.finalAnswer && (
                <div className="ws-assistant-row">
                  <div className="ws-assistant-name">EvoTeam</div>
                  <p className="ws-assistant-text">{conversation.finalAnswer}</p>
                  <div className="ws-artifact-row">
                    <FileText size={13} />
                    <span>发布排期 project-plan.json</span>
                    <span className="tiny">Plan · 12 工作项</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
      <div className="ws-composer-dock">
        <Composer
          running={running}
          onSubmit={onSubmit}
          onStop={conversation.running ? stop : undefined}
        />
      </div>
    </div>
  );
}