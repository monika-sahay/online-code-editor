"use client";

import { useEffect, useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import type * as MonacoType from "monaco-editor";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

type Language = "python" | "r";

const defaultPy = `# Welcome to the Online Python Code Editor
# Write your Python code below and click "Run Code" to execute

print("Hello, World!")
print("This is working perfectly!")

# Try some calculations
x = 10
y = 5
print(f"{x}  {y} = {x  y}")
print(f"{x} * {y} = {x * y}")
`;

const defaultR = `# Welcome to the Online R Code Editor
# Write your R code below and click "Run Code" to execute

cat("Hello, World!\\n")
cat("This is working perfectly!\\n")
x <- 10; y <- 5
cat(x, "", y, "=", x  y, "\\n")
cat(x, "*", y, "=", x * y, "\\n")
`;

interface ExecutionResult {
  output: string;
  error: string;
  success: boolean;
}

export default function CodeEditor() {
  const [language, setLanguage] = useState<Language>("python");
  const [code, setCode] = useState<string>(defaultPy);
  const [output, setOutput] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  // When language changes, swap in the matching default snippet (optional)
  useEffect(() => {
    setCode(language === "python" ? defaultPy : defaultR);
  }, [language]);

  const executeCode = async () => {
    if (!code.trim()) {
      setError("Please enter some code to execute");
      return;
    }

    setIsLoading(true);
    setError("");
    setOutput("");

    try {
      // Use relative URL for better compatibility
      const BACKEND_URL =
        process.env.NODE_ENV === "production"
          ? "https://online-code-editor-idoc.onrender.com/execute"
          : "https://2jfjkj-8001.csb.app/execute";

      const response = await fetch(`${BACKEND_URL}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ code, language }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result: ExecutionResult = await response.json();

      if (result.success) {
        setOutput(result.output || "Code executed successfully (no output)");
        if (result.error) {
          setError(result.error);
        }
      } else {
        setError(result.error || "Execution failed");
        setOutput(result.output || "");
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? `Network error: ${err.message}. Please ensure the backend server is running on port 8001.`
          : "An unexpected error occurred"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const clearOutput = () => {
    setOutput("");
    setError("");
  };
  const editorRef = useRef<MonacoType.editor.IStandaloneCodeEditor | null>(
    null
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                Online Code Editor
              </h1>
              <p className="text-sm text-muted-foreground">
                Write and execute{" "}
                <span className="font-medium">{language.toUpperCase()}</span>{" "}
                code in a sandboxed environment
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={clearOutput}
                variant="outline"
                disabled={isLoading}
              >
                Clear Output
              </Button>
              <Button
                onClick={executeCode}
                disabled={isLoading || !code.trim()}
                className="min-w-[100px]"
              >
                {isLoading ? "Running..." : "Run Code"}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-200px)]">
          {/* Code Editor */}
          <Card className="flex flex-col">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">
                  {language.toUpperCase()} Code Editor
                </CardTitle>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    Language:
                  </span>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value as Language)}
                    className="border rounded px-2 py-1 text-sm"
                  >
                    <option value="python">Python</option>
                    <option value="r">R</option>
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-0">
              <div className="h-full border rounded-md overflow-hidden">
                <Editor
                  height="500px"
                  language={language === "python" ? "python" : "r"}
                  defaultLanguage="python"
                  defaultValue={defaultPy}
                  value={code}
                  onChange={(value) => setCode(value ?? "")}
                  onMount={(
                    editor: MonacoType.editor.IStandaloneCodeEditor,
                    monaco: typeof MonacoType
                  ) => {
                    editorRef.current = editor;
                    // Register completion provider here!
                    monaco.languages.registerCompletionItemProvider("python", {
                      triggerCharacters: ["\n", " ", ".", ":"],
                      provideCompletionItems: async (model, position) => {
                        const code = model.getValue();
                        const cursorOffset = model.getOffsetAt(position);
                        const AI_AUTOCOMPLETE_URL =
                          process.env.NODE_ENV === "production"
                            ? "https://online-code-editor-idoc.onrender.com/ai-complete"
                            : "https://2jfjkj-8001.csb.app/ai-complete";
                        const response = await fetch(AI_AUTOCOMPLETE_URL, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ code, cursorOffset }),
                        });
                        const data = await response.json();

                        return {
                          suggestions: [
                            {
                              label: "AI Suggestion",
                              kind: monaco.languages.CompletionItemKind.Snippet,
                              insertText: data.suggestion,
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

                    // Minimal R language registration if Monaco doesn't have it
                    const hasR = monaco.languages
                      .getLanguages()
                      .some(
                        (l: MonacoType.languages.ILanguageExtensionPoint) =>
                          l.id === "r"
                      );
                    if (!hasR) {
                      monaco.languages.register({ id: "r" });

                      const rLanguage: MonacoType.languages.IMonarchLanguage = {
                        tokenizer: {
                          root: [
                            [/#.*/, "comment"],
                            [/\"([^\"\\]|\\.)*\"/, "string"],
                            [/'([^'\\]|\\.)*'/, "string"],
                            [/\\b(\\d+(\\.\\d+)?)\\b/, "number"],
                            [
                              /\\b(function|if|else|for|while|repeat|in|next|break|TRUE|FALSE|NULL|NA|NaN|Inf)\\b/,
                              "keyword",
                            ],
                            // put '-' first to avoid char class range issues
                            [/[-+*/=<>!]+/, "operator"],
                            [/[a-zA-Z_][\\w.]*/, "identifier"],
                            [/[[\\](){}]/, "@brackets"],
                          ],
                        },
                      };
                      monaco.languages.setMonarchTokensProvider("r", rLanguage);
                    }
                  }}
                  theme="vs-dark"
                  options={{
                    fontSize: 16,
                    minimap: { enabled: false },
                    suggestOnTriggerCharacters: true,
                  }}
                />
              </div>
            </CardContent>
          </Card>

          {/* Output Panel */}
          <Card className="flex flex-col">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Output</CardTitle>
            </CardHeader>
            <CardContent className="flex-1">
              <div className="h-full">
                {isLoading && (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
                      <p className="text-sm text-muted-foreground">
                        Executing code...
                      </p>
                    </div>
                  </div>
                )}

                {!isLoading && (output || error) && (
                  <div className="space-y-4">
                    {output && (
                      <div>
                        <h4 className="text-sm font-medium text-green-600 mb-2">
                          Output:
                        </h4>
                        <pre className="bg-muted p-3 rounded-md text-sm overflow-auto whitespace-pre-wrap">
                          {output}
                        </pre>
                      </div>
                    )}

                    {error && (
                      <>
                        {output && <Separator />}
                        <div>
                          <h4 className="text-sm font-medium text-red-600 mb-2">
                            Error:
                          </h4>
                          <pre className="bg-red-50 border border-red-200 p-3 rounded-md text-sm text-red-700 overflow-auto whitespace-pre-wrap">
                            {error}
                          </pre>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {!isLoading && !output && !error && (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <div className="text-center">
                      <p className="text-lg mb-2">Ready to execute</p>
                      <p className="text-sm">
                        Click {"Run Code"} to see the output here
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Connection Status */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-lg">Connection Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-muted-foreground">
              <p>
                Backend API: http://localhost:8001/execute (sends{" "}
                {"{ code, language }"})
              </p>
              <p>Frontend: http://localhost:8000</p>
              <p className="mt-2">
                If you see network errors, ensure both servers are running:
              </p>
              <ul className="mt-1 space-y-1">
                <li>• Backend: uvicorn main:app --host 0.0.0.0 --port 8001</li>
                <li>• Frontend: npm run dev</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
