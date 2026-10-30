import { Modal } from "./Modal";
import { Button } from "./Button";
interface Props { open: boolean; onClose: () => void; onConfirm: () => void; title: string; message: string; confirmLabel?: string; loading?: boolean; }
export function ConfirmDialog({ open, onClose, onConfirm, title, message, confirmLabel = "ยืนยัน", loading }: Props) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-muted-strong">{message}</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose} disabled={loading}>ยกเลิก</Button>
        <Button variant="danger" onClick={onConfirm} loading={loading}>{confirmLabel}</Button>
      </div>
    </Modal>
  );
}
