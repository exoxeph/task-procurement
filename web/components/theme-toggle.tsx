"use client";

import { useState } from "react";

export function ThemeToggle() {
  const [theme, setTheme] = useState("system");
  function toggle() {
    const next =
      theme === "system" ? "light" : theme === "light" ? "dark" : "system";
    setTheme(next);
    if (next === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = next;
  }
  return (
    <button
      className="theme"
      onClick={toggle}
      aria-label={`Theme: ${theme}. Change theme`}
    >
      ◐ {theme.charAt(0).toUpperCase() + theme.slice(1)}
    </button>
  );
}
