/* react-i18next 初始化。词典迁移自设计稿 i18n.js 的 MIO_STRINGS（zh → en）。
   中文是源语言：词条的 key 就是中文原文，en 提供译文。
   字段名 / 状态枚举 / 文件路径（as_of / conviction / FieldMeta / US.AAPL）
   是契约标识符，两种语言下都保持原样。 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";

i18n.use(initReactI18next).init({
  lng: "zh",
  fallbackLng: false, // 没有译文时回退到 key 本身（即中文原文）
  resources: { en: { translation: en } },
  keySeparator: false,
  nsSeparator: false,
  interpolation: { escapeValue: false },
  returnNull: false,
  returnEmptyString: false,
});

export default i18n;

/** 源串翻译：en 查词典，zh 返回原文。模块级调用，语言切换靠 App 整树重挂。 */
export function tt(zh: string): string {
  return i18n.t(zh);
}

/** 双语二选一（设计稿 bi(zh, en) 的直迁移）。 */
export function bi<T = string>(zh: T, enText: T): T {
  return i18n.language === "en" ? enText : zh;
}
