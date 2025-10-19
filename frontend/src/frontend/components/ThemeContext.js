import React, { createContext, useContext, useState, useEffect } from "react";

// Create Context
export const ThemeContext = createContext();

// Provider Component
export function ThemeProvider({ children }) {
  // initialize from localStorage (use lowercase 'light'/'dark'); treat 'system' as 'light'
  const rawStored = (typeof window !== 'undefined' && localStorage.getItem('chatTheme')) || 'light';
  const stored = rawStored && rawStored.toLowerCase() === 'system' ? 'light' : rawStored;
  const [theme, setThemeState] = useState(stored || 'light'); // 'light' | 'dark'
  const [fontSize, setFontSize] = useState('medium'); // small | medium | large

  // wrapper to persist and set body class
  const setTheme = (t) => {
    // normalize and treat 'system' as 'light' for now
    let norm = (t || 'light').toString().toLowerCase();
    if (norm === 'system') norm = 'light';
    setThemeState(norm);
    try {
      // still persist the original requested value if caller wants 'system' preserved
      localStorage.setItem('chatTheme', norm);
    } catch {}
    // keep a body class for global CSS selectors (.dark-theme .foo)
    if (typeof document !== 'undefined') {
  document.body.classList.remove('light-theme', 'dark-theme');
  document.body.classList.add(`${norm}-theme`);
  document.body.setAttribute('data-theme', norm);
    }
  };

  // Ensure body has initial class on mount
  useEffect(() => {
    try {
      const norm = (theme || 'light').toString().toLowerCase();
      document.body.classList.remove('light-theme', 'dark-theme');
      document.body.classList.add(`${norm}-theme`);
      document.body.setAttribute('data-theme', norm);
      document.body.setAttribute('data-font', fontSize || 'medium');
    } catch {}
  }, [theme, fontSize]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, fontSize, setFontSize }}>
      {children}
    </ThemeContext.Provider>
  );
}

// 🔹 Custom hook for easier usage
export function useTheme() {
  return useContext(ThemeContext);
}
