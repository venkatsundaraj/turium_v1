import { Inbox } from "@/components/Inbox";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-8">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">AI Knowledge Inbox</h1>
        <p className="text-sm text-zinc-500">Save notes and links, then ask questions answered from them with citations.</p>
      </header>
      <Inbox />
    </main>
  );
}
