export type Language = "python" | "r";

export interface ExecutionResult {
  output: string;
  error: string;
  success: boolean;
}
