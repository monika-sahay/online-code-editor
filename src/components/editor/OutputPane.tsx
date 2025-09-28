"use client";

import { Separator } from "@/components/ui/separator";

interface Props {
  isLoading: boolean;
  output: string;
  error: string;
}

export default function OutputPane({ isLoading, output, error }: Props) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">Executing code...</p>
        </div>
      </div>
    );
  }

  if (!output && !error) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <p className="text-lg mb-2">Ready to execute</p>
          <p className="text-sm">Click {"Run Code"} to see the output here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {output && (
        <div>
          <h4 className="text-sm font-medium text-green-600 mb-2">Output:</h4>
          <pre className="bg-muted p-3 rounded-md text-sm overflow-auto whitespace-pre-wrap">
            {output}
          </pre>
        </div>
      )}
      {error && (
        <>
          {output && <Separator />}
          <div>
            <h4 className="text-sm font-medium text-red-600 mb-2">Error:</h4>
            <pre className="bg-red-50 border border-red-200 p-3 rounded-md text-sm text-red-700 overflow-auto whitespace-pre-wrap">
              {error}
            </pre>
          </div>
        </>
      )}
    </div>
  );
}
