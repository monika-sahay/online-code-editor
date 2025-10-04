"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import LanguageSelect from "@/components/editor/LanguageSelect";
import CodePane from "@/components/editor/CodePane";
import OutputPane from "@/components/editor/OutputPane";
import {
  defaultPy,
  defaultR,
  defaultBash,
  defaultCpp,
  defaultC,
  defaultCSharp,
  defaultGo,
  defaultJS,
  defaultJava,
  defaultJulia,
} from "@/constants/snippets";
import { runCode } from "@/utils/api";
import type { ExecutionResult, Language } from "@/types/editor";
import ConnectionStatus from "@/components/ConnectionStatus";

export default function CodeEditorPage() {
  const [language, setLanguage] = useState<Language>("python");
  const [code, setCode] = useState<string>(defaultPy);
  const [output, setOutput] = useState<string>("");
  const [err, setErr] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    const map = {
      python: defaultPy,
      r: defaultR,
      javascript: defaultJS,
      bash: defaultBash,
      cpp: defaultCpp,
      c: defaultC,
      csharp: defaultCSharp,
      java: defaultJava,
      go: defaultGo,
      julia: defaultJulia,
    } as const;

    setCode(map[language] ?? defaultPy);
  }, [language]);

  const onRun = async () => {
    if (!code.trim()) {
      setErr("Please enter some code to execute");
      return;
    }
    setLoading(true);
    setErr("");
    setOutput("");
    try {
      const res: ExecutionResult = await runCode(code, language);
      if (res.success) {
        setOutput(res.output || "Code executed successfully (no output)");
        if (res.error) setErr(res.error);
      } else {
        setErr(res.error || "Execution failed");
        setOutput(res.output || "");
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const onClear = () => {
    setOutput("");
    setErr("");
  };

  return (
    <div className="min-h-screen bg-background">
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
              <Button onClick={onClear} variant="outline" disabled={loading}>
                Clear Output
              </Button>
              <Button
                onClick={onRun}
                disabled={loading || !code.trim()}
                className="min-w-[100px]"
              >
                {loading ? "Running..." : "Run Code"}
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-200px)]">
          <Card className="flex flex-col">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">
                  {language.toUpperCase()} Code Editor
                </CardTitle>
                <LanguageSelect value={language} onChange={setLanguage} />
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-0">
              <div className="h-full border rounded-md overflow-hidden">
                <CodePane language={language} code={code} setCode={setCode} />
              </div>
            </CardContent>
          </Card>

          <Card className="flex flex-col">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Output</CardTitle>
            </CardHeader>
            <CardContent className="flex-1">
              <OutputPane isLoading={loading} output={output} error={err} />
            </CardContent>
          </Card>
        </div>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-lg">Connection Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-muted-foreground">
              <ConnectionStatus />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
