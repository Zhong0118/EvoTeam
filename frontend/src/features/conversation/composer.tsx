/* Composer — V3 §10. Coding-Agent style: chips row, growing textarea,
   bottom tool row. Queue/Steer depend on the backend and are shown as
   explicitly disabled, never faked. */
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import {
  AtSign,
  ChevronDown,
  Plus,
  Send,
  Square,
} from "lucide-react";

export function Composer({
  running = false,
  onSubmit,
  onStop,
  placeholder = "输入任务，或继续当前任务……",
}: {
  running?: boolean;
  onSubmit?: (text: string) => void;
  onStop?: () => void;
  placeholder?: string;
}) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [text]);

  function submit() {
    const value = text.trim();
    if (!value) return;
    onSubmit?.(value);
    setText("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Escape stops an in-flight run when the draft is empty (OpenCode's
    // working && blank rule); never steals Escape while composing text.
    if (event.key === "Escape" && running && !text.trim()) {
      onStop?.();
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      // IME guard: Enter during composition (Chinese input) must not submit.
      if (event.nativeEvent.isComposing || event.keyCode === 229) return;
      event.preventDefault();
      if (running && !text.trim()) onStop?.();
      else submit();
    }
  }

  return (
    <div className="ws-composer">
      <div className="ws-composer-box">
        <div className="ws-chip-row" hidden={!running}>
          <span className="ws-context-chip">
            <span className="ws-status-dot pulse" /> 执行中 · Strategy 快照已固定
          </span>
        </div>
        <textarea
          ref={inputRef}
          className="ws-composer-input"
          rows={1}
          value={text}
          placeholder={placeholder}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          aria-label="任务输入"
        />
        <div className="ws-composer-bar">
          <button className="ws-tool-button" aria-label="添加附件" title="附件上传尚未接入后端">
            <Plus size={15} />
          </button>
          <button className="ws-tool-button" title="运行模式">
            Auto <ChevronDown size={12} />
          </button>
          <button className="ws-tool-button" title="权限">
            权限 <ChevronDown size={12} />
          </button>
          <button
            className="ws-tool-button"
            aria-disabled
            title="@文件 / 知识引用待后端接入（R4）"
            style={{ opacity: 0.45 }}
          >
            <AtSign size={14} /> 上下文
          </button>
          <span className="ws-composer-spacer" />
          <button className="ws-tool-button" title="模型由服务端配置决定">
            deepseek-v4-flash <ChevronDown size={12} />
          </button>
          {running && !text.trim() ? (
            <button
              className="ws-send-button"
              aria-label="停止执行"
              onClick={onStop}
            >
              <Square size={12} />
            </button>
          ) : (
            <button
              className="ws-send-button"
              aria-label="发送任务"
              disabled={!text.trim()}
              onClick={submit}
            >
              <Send size={13} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
