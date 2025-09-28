"use client";

import Editor from "@monaco-editor/react";
import type * as Monaco from "monaco-editor";
import { useRef } from "react";
import { aiComplete } from "@/utils/api";
import { ensureMonacoR } from "./monacoR";
import type { Language } from "@/types/editor";

interface Props {
  language: Language;
  code: string;
  setCode: (code: string) => void;
}

export default function CodePane({ language, code, setCode }: Props) {
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);

  return (
    <Editor
      height="500px"
      language={language === "python" ? "python" : "r"}
      value={code}
      onChange={(val) => setCode(val ?? "")}
      onMount={(editor, monaco) => {
        editorRef.current = editor;

        // Python AI completion
        monaco.languages.registerCompletionItemProvider("python", {
          triggerCharacters: ["\n", " ", ".", ":"],
          provideCompletionItems: async (model, position) => {
            const codeText = model.getValue();
            const cursorOffset = model.getOffsetAt(position);
            const suggestion = await aiComplete(codeText, cursorOffset);

            return {
              suggestions: [
                {
                  label: "AI Suggestion",
                  kind: monaco.languages.CompletionItemKind.Snippet,
                  insertText: suggestion,
                  range: {
                    startLineNumber: position.lineNumber,
                    endLineNumber: position.lineNumber,
                    startColumn: position.column,
                    endColumn: position.column,
                  },
                  documentation: "Powered by OpenAI",
                },
              ],
            };
          },
        });

        // Minimal R highlighting if missing
        ensureMonacoR(monaco);
      }}
      theme="vs-dark"
      options={{
        fontSize: 16,
        minimap: { enabled: false },
        suggestOnTriggerCharacters: true,
      }}
    />
  );
}
