"use client";

import { useItems } from "@/hooks/useItems";
import { AskPanel } from "./AskPanel";
import { IngestForm } from "./IngestForm";
import { ItemList } from "./ItemList";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-sm font-semibold">{title}</h2>
      {children}
    </section>
  );
}

export function Inbox() {
  const { items, total, loading, error, refresh, ingest } = useItems();

  return (
    <div className="grid gap-10 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <div className="flex flex-col gap-8">
        <Section title="Add to inbox">
          <IngestForm onIngest={ingest} />
        </Section>
        <Section title="Saved items">
          <ItemList items={items} total={total} loading={loading} error={error} onRetry={refresh} />
        </Section>
      </div>
      <Section title="Ask your inbox">
        <AskPanel />
      </Section>
    </div>
  );
}
