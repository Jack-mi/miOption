/* UI 偏好持久化：localStorage + 枚举迁移校验。
   读取时校验每个值是否在合法枚举内，不在则回退默认值——
   原型曾因残留旧屏名导致内容区全空，这里必须拦。 */
import { useCallback, useState } from "react";

const KEY = "mioption.workbench.prefs.v1";

const ENUMS: Record<string, string[]> = {
  direction: ["paper", "desk", "hunt"],
  theme: ["light", "dark"],
  accent: ["auto", "clay", "indigo", "amber", "teal"],
  density: ["compact", "regular", "airy"],
  screen: ["home", "main", "watch", "wiki"],
  lang: ["zh", "en"],
  drawerTab: ["cov", "runs", "risk"],
};

export interface Prefs {
  direction: string;
  theme: string;
  accent: string;
  density: string;
  screen: string;
  ticker: string;
  drawer: boolean;
  drawerTab: string;
  lang: string;
}

const DEFAULTS: Prefs = {
  direction: "paper",
  theme: "light",
  accent: "auto",
  density: "regular",
  screen: "home",
  ticker: "US.AAPL",
  drawer: false,
  drawerTab: "cov",
  lang: "zh",
};

function migrate(raw: any): Prefs {
  const out: Prefs = { ...DEFAULTS };
  if (!raw || typeof raw !== "object") return out;
  for (const k of Object.keys(ENUMS)) {
    const v = raw[k];
    if (typeof v === "string" && ENUMS[k].includes(v)) (out as any)[k] = v;
  }
  if (typeof raw.ticker === "string" && raw.ticker) out.ticker = raw.ticker;
  out.drawer = raw.drawer === true;
  return out;
}

function load(): Prefs {
  try {
    return migrate(JSON.parse(localStorage.getItem(KEY) || "null"));
  } catch {
    return { ...DEFAULTS };
  }
}

export function usePrefs(): [Prefs, (k: keyof Prefs, v: any) => void] {
  const [prefs, setPrefs] = useState<Prefs>(load);
  const set = useCallback((k: keyof Prefs, v: any) => {
    setPrefs((s) => {
      const next = { ...s, [k]: v };
      try {
        localStorage.setItem(KEY, JSON.stringify(next));
      } catch { /* 隐私模式下静默 */ }
      return next;
    });
  }, []);
  return [prefs, set];
}
