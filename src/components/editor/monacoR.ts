import type * as Monaco from "monaco-editor";

export function ensureMonacoR(monaco: typeof Monaco): void {
  const hasR = monaco.languages.getLanguages().some((l) => l.id === "r");
  if (hasR) return;

  monaco.languages.register({ id: "r" });

  const rLanguage: Monaco.languages.IMonarchLanguage = {
    tokenizer: {
      root: [
        [/#.*/, "comment"],
        [/\"([^\"\\]|\\.)*\"/, "string"],
        [/'([^'\\]|\\.)*'/, "string"],
        [/\b(\d+(\.\d+)?)\b/, "number"],
        [
          /\b(function|if|else|for|while|repeat|in|next|break|TRUE|FALSE|NULL|NA|NaN|Inf)\b/,
          "keyword",
        ],
        // put '-' first to avoid char class range issues
        [/[-+*/=<>!]+/, "operator"],
        [/[a-zA-Z_][\w.]*/, "identifier"],
        [/[\[\]\(\){}]/, "@brackets"],
      ],
    },
  };
  monaco.languages.setMonarchTokensProvider("r", rLanguage);
}
