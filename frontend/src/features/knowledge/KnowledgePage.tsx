import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { knowledge } from "../../lib/services";
import { PageHeader, LoadingState, ErrorState } from "../../components/common";
export function KnowledgePage() {
  const [input, setInput] = useState("");
  const search = useMutation({ mutationFn: knowledge.search });
  function submit(e: FormEvent) {
    e.preventDefault();
    if (input.trim()) search.mutate(input.trim());
  }
  return (
    <>
      <PageHeader
        eyebrow="TRUSTED INFORMATION"
        title="Clinic guide"
        description="Answers from approved clinic policy documents, with sources when available."
      />
      <form className="search-bar" onSubmit={submit}>
        <Search size={20} />
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="What is the cancellation policy?"
          aria-label="Ask a clinic policy question"
        />
        <button className="button" disabled={search.isPending}>
          Ask
        </button>
      </form>
      {search.isPending && <LoadingState />}
      {search.isError && (
        <ErrorState message={(search.error as Error).message} />
      )}{" "}
      {search.data && (
        <div className="card details-card">
          <span className="eyebrow">
            {search.data.grounded ? "FROM THE KNOWLEDGE BASE" : "NOT VERIFIED"}
          </span>
          <h2>Answer</h2>
          <p>{search.data.answer}</p>
          {search.data.sources.length > 0 && (
            <div className="source-list">
              <strong>Sources</strong>
              {search.data.sources.map((s) => (
                <p key={s.document_id}>
                  {s.title} · {s.source} · v{s.version}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}
