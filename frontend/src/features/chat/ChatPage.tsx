import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageCircle, Trash2 } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { chat, conversations } from "../../lib/services";
import { PageHeader, LoadingState, ErrorState } from "../../components/common";
export function ChatPage() {
  const { session } = useAuth();
  const [searchParams] = useSearchParams();
  const [selected, setSelected] = useState<string | null>(() =>
    searchParams.get("conversation"),
  );
  const [input, setInput] = useState("");
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ["conversations", session?.user.id],
    queryFn: conversations.list,
  });
  const detail = useQuery({
    queryKey: ["conversation", selected],
    queryFn: () => conversations.detail(selected!),
    enabled: Boolean(selected),
  });
  const create = useMutation({
    mutationFn: conversations.create,
    onSuccess: (c) => {
      setSelected(c.id);
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
  const remove = useMutation({
    mutationFn: conversations.remove,
    onSuccess: (_result, id) => {
      if (selected === id) setSelected(null);
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
  const send = useMutation({
    mutationFn: async (message: string) => {
      const id = selected ?? (await conversations.create()).id;
      setSelected(id);
      await chat.send(id, message);
      return id;
    },
    onSuccess: (id) => {
      setInput("");
      void queryClient.invalidateQueries({ queryKey: ["conversation", id] });
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
  function submit(e: FormEvent) {
    e.preventDefault();
    if (input.trim() && !send.isPending) send.mutate(input.trim());
  }
  return (
    <>
      <PageHeader
        eyebrow="HERE TO HELP"
        title="AI appointment assistant"
        description="Ask about doctors, times, appointments, or clinic policies."
      />
      <div className="chat-layout">
        <aside className="conversation-panel">
          <button
            className="button full"
            disabled={create.isPending}
            onClick={() => create.mutate()}
          >
            New conversation
          </button>
          {list.isLoading ? (
            <LoadingState />
          ) : list.isError ? (
            <ErrorState message="History unavailable." />
          ) : list.data?.length ? (
            list.data.map((c) => (
              <div className="conversation-row" key={c.id}>
                <button
                  className={`conversation-link ${selected === c.id ? "selected" : ""}`}
                  onClick={() => setSelected(c.id)}
                >
                  {c.title}
                </button>
                <button
                  className="icon-button"
                  aria-label={`Delete ${c.title}`}
                  disabled={remove.isPending}
                  onClick={() => {
                    if (window.confirm(`Delete ${c.title}?`))
                      remove.mutate(c.id);
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          ) : (
            <p className="muted">No conversations yet.</p>
          )}
        </aside>
        <section className="chat-panel" aria-label="Conversation">
          <div className="messages">
            {detail.isLoading ? (
              <LoadingState />
            ) : detail.isError ? (
              <ErrorState message="Conversation could not be loaded." />
            ) : detail.data?.messages.length ? (
              detail.data.messages.map((m) => (
                <div
                  className={`message ${m.role.toLowerCase() === "user" ? "user" : "assistant"}`}
                  key={m.id}
                >
                  <small>
                    {m.role.toLowerCase() === "user"
                      ? "You"
                      : "CarePath assistant"}
                  </small>
                  <p>{m.content}</p>
                </div>
              ))
            ) : (
              <div className="chat-empty">
                <MessageCircle size={32} />
                <h2>How can I help today?</h2>
                <p>Ask about finding a doctor or managing an appointment.</p>
              </div>
            )}
            {send.isPending && (
              <div className="message assistant" role="status">
                Thinking…
              </div>
            )}
          </div>
          <form className="chat-form" onSubmit={submit}>
            <textarea
              aria-label="Message"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder="Ask about doctors or appointments…"
              rows={2}
            />
            <button
              className="button"
              disabled={!input.trim() || send.isPending}
            >
              Send
            </button>
          </form>
          {send.isError && (
            <p className="error-text" role="alert">
              {(send.error as Error).message}
            </p>
          )}
        </section>
      </div>
    </>
  );
}
