import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useState } from "react";

type Mode = "terminal" | "academic";
const ModeContext = createContext<{ mode: Mode; setMode: (m: Mode) => void }>({ mode: "terminal", setMode: () => {} });

const STORAGE_KEY = "treasuryx-mode";

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<Mode>(() => (localStorage.getItem(STORAGE_KEY) as Mode) || "terminal");

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  return <ModeContext.Provider value={{ mode, setMode: setModeState }}>{children}</ModeContext.Provider>;
}

export function useMode() {
  return useContext(ModeContext);
}
