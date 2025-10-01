export type Language =
  | "python"
  | "r"
  | "javascript"
  | "bash"
  | "cpp"
  | "java"
  | "go"
  | "julia";

export interface ExecutionResult {
  output: string;
  error: string;
  success: boolean;
}
