import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageCircle, Trash2 } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { chat, conversations } from "../../lib/services";
import { recoverProposal } from "../../lib/proposal-recovery";
import {
  PageHeader,
  LoadingState,
  ErrorState,
  ProposalDialog,
} from "../../components/common";
import type { Proposal, ProposalReference } from "../../types/api";
export function ChatPage() {
  const { session } = useAuth();
  const [searchParams] = useSearchParams();
  const [selected, setSelected] = useState<string | null>(() =>
    searchParams.get("conversation"),
  );
  const [input, setInput] = useState("");
  const [pendingProposal, setPendingProposal] = useState<{
    conversationId: string;
    proposal: Proposal;
  } | null>(null);
  const [proposalOpen, setProposalOpen] = useState(false);
  const [proposalResolved, setProposalResolved] = useState(false);
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
      if (pendingProposal?.conversationId === id) setPendingProposal(null);
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
  const recover = useMutation({
    mutationFn: ({
      reference,
    }: {
      reference: ProposalReference;
      conversationId: string;
    }) => recoverProposal(reference),
    onSuccess: (proposal, variables) => {
      setPendingProposal({
        conversationId: variables.conversationId,
        proposal,
      });
      setProposalResolved(false);
      setProposalOpen(true);
    },
  });
  const send = useMutation({
    mutationFn: async (message: string) => {
      const id = selected ?? (await conversations.create()).id;
      setSelected(id);
      const response = await chat.send(id, message);
      return { id, response };
    },
    onSuccess: ({ id, response }) => {
      setInput("");
      void queryClient.invalidateQueries({ queryKey: ["conversation", id] });
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
      let proposal: Proposal | null = null;
      if (response.requires_hitl && response.booking_proposal)
        proposal = { kind: "booking", data: response.booking_proposal };
      else if (response.requires_hitl && response.cancellation_proposal)
        proposal = {
          kind: "cancellation",
          data: response.cancellation_proposal,
        };
      else if (response.requires_hitl && response.rescheduling_proposal)
        proposal = {
          kind: "rescheduling",
          data: response.rescheduling_proposal,
        };
      if (proposal) {
        setPendingProposal({ conversationId: id, proposal });
        setProposalResolved(false);
        setProposalOpen(true);
      }
    },
  });
  function submit(e: FormEvent) {
    e.preventDefault();
    if (input.trim() && !send.isPending && !recover.isPending)
      send.mutate(input.trim());
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
            disabled={create.isPending || send.isPending || recover.isPending}
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
                  disabled={send.isPending || recover.isPending}
                  onClick={() => setSelected(c.id)}
                >
                  {c.title}
                </button>
                <button
                  className="icon-button"
                  aria-label={`Delete ${c.title}`}
                  disabled={
                    remove.isPending || send.isPending || recover.isPending
                  }
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
          {pendingProposal?.conversationId === selected && !proposalOpen && (
            <button
              className="button secondary"
              onClick={() => setProposalOpen(true)}
            >
              Review pending request
            </button>
          )}
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
                  {m.role.toLowerCase() === "assistant" &&
                    m.proposal_reference &&
                    selected && (
                      <button
                        className="text-button"
                        disabled={recover.isPending}
                        onClick={() =>
                          recover.mutate({
                            reference: m.proposal_reference!,
                            conversationId: selected,
                          })
                        }
                      >
                        {recover.isPending
                          ? "Checking request…"
                          : "Review request"}
                      </button>
                    )}
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
              disabled={send.isPending || recover.isPending}
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
              disabled={!input.trim() || send.isPending || recover.isPending}
            >
              Send
            </button>
          </form>
          {send.isError && (
            <p className="error-text" role="alert">
              {(send.error as Error).message}
            </p>
          )}
          {recover.isError && (
            <p className="error-text" role="alert">
              {(recover.error as Error).message}
            </p>
          )}
        </section>
      </div>
      <ProposalDialog
        proposal={proposalOpen ? (pendingProposal?.proposal ?? null) : null}
        onDecisionCompleted={() => setProposalResolved(true)}
        onClose={() => {
          setProposalOpen(false);
          if (proposalResolved) setPendingProposal(null);
        }}
      />
    </>
  );
}
