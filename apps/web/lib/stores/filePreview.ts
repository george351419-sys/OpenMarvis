"use client";

import { create } from "zustand";

interface FilePreviewStore {
  path: string | null;
  open: (path: string) => void;
  close: () => void;
}

function decodePath(p: string): string {
  try { return decodeURIComponent(p); } catch { return p; }
}

export const useFilePreview = create<FilePreviewStore>((set) => ({
  path: null,
  open: (path) => set({ path: decodePath(path) }),
  close: () => set({ path: null }),
}));
