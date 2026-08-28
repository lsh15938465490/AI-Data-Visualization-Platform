import { ElMessage } from "element-plus";

export function toastSuccess(message: string) {
  ElMessage({ message, type: "success", duration: 2500, showClose: true });
}

export function toastError(message: string) {
  ElMessage({ message, type: "error", duration: 4500, showClose: true });
}

export function toastWarning(message: string) {
  ElMessage({ message, type: "warning", duration: 3500, showClose: true });
}
