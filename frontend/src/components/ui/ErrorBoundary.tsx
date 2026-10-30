import { Component, type ErrorInfo, type ReactNode } from "react";
interface S { error: Error | null }
export class ErrorBoundary extends Component<{ children: ReactNode }, S> {
  state: S = { error: null };
  static getDerivedStateFromError(e: Error): S { return { error: e }; }
  componentDidCatch(e: Error, i: ErrorInfo) { console.error("ErrorBoundary:", e, i); }
  render() {
    if (this.state.error) return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="font-medium">เกิดข้อผิดพลาดที่ไม่คาดคิด</p>
        <p className="max-w-sm text-sm text-muted-strong">{this.state.error.message}</p>
        <button type="button" className="text-sm text-brand underline" onClick={() => this.setState({ error: null })}>ลองอีกครั้ง</button>
      </div>
    );
    return this.props.children;
  }
}
