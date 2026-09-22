import { useState, type FormEvent } from "react";

interface Props {
  onSubmit: (query: string) => void;
}

export default function QueryBox({ onSubmit }: Props) {
  const [value, setValue] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const query = value.trim();
    if (query) onSubmit(query);
  };

  return (
    <form className="query" onSubmit={submit} role="search">
      <svg className="query__icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.6-3.6" />
      </svg>
      <input
        className="query__input"
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask anything about these brands..."
        aria-label="Ask anything about these brands"
        autoComplete="off"
        spellCheck={false}
      />
      <button className="query__submit" type="submit" aria-label="Ask" disabled={!value.trim()}>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      </button>
    </form>
  );
}
