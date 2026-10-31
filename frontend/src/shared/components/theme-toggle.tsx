import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/shared/hooks/use-theme";
import { Button } from "@/shared/ui/button";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const label = isDark ? "Helles Design aktivieren" : "Dunkles Design aktivieren";

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      data-testid="app-btn-theme-toggle"
    >
      {isDark ? <Sun /> : <Moon />}
    </Button>
  );
}
