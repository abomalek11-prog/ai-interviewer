import { Bell, BrainCircuit, Grid2X2, LineChart, MessageSquareText, Search, Send, Settings, UserCircle, UsersRound } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: Grid2X2 },
  { to: "/interviews", label: "Interviews", icon: MessageSquareText },
  { to: "/candidates", label: "Candidates", icon: UsersRound },
  { to: "/analytics", label: "Analytics", icon: LineChart },
  { to: "/profile", label: "Profile", icon: UserCircle },
];

function initialsOf(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function AppShell() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const initials = user ? initialsOf(user.full_name) : "";

  return (
    <main className="grid min-h-screen grid-cols-[248px_minmax(0,1fr)] bg-background">
      <aside className="sticky top-0 flex h-screen flex-col border-r border-border bg-white/90 p-4">
        <div className="flex items-center gap-3 px-2 pt-0.5 pb-7">
          <div className="grid size-[42px] place-items-center rounded-lg bg-secondary text-white">
            <BrainCircuit size={24} strokeWidth={2.4} />
          </div>
          <div>
            <strong className="block text-2xl leading-none">InterviewAI</strong>
            <span className="mt-1 block font-mono text-[10px] tracking-[2px] text-foreground/70">AI-DRIVEN INSIGHTS</span>
          </div>
        </div>

        <nav className="grid gap-1.5" aria-label="Primary navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex min-h-11 items-center gap-3 rounded-lg px-3.5 text-base text-foreground/80",
                    isActive && "bg-white font-extrabold text-secondary shadow-[inset_-3px_0_0_theme(colors.secondary)]",
                  )
                }
              >
                <Icon size={21} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="mt-auto flex items-center gap-2.5 border-t border-border pt-4">
          <Avatar className="size-[34px]">
            {user?.profile_picture_url && <AvatarImage src={user.profile_picture_url} alt={user.full_name} />}
            <AvatarFallback className="text-xs">{initials}</AvatarFallback>
          </Avatar>
          <div>
            <strong className="block font-mono text-sm">{user?.full_name}</strong>
            <span className="block font-mono text-xs text-muted-foreground">{user?.title ?? "Recruiter"}</span>
          </div>
        </div>

        <Button className="mt-3.5 w-full" onClick={() => navigate("/interviews/new")}>
          <Send size={18} />
          <span>New Interview</span>
        </Button>
      </aside>

      <section className="min-w-0">
        <header className="flex min-h-16 items-center justify-between gap-4 border-b border-border bg-background/95 px-7 py-2.5">
          <label className="flex h-10 w-full max-w-[560px] items-center gap-2 rounded-full bg-muted px-3.5 text-foreground/80">
            <Search size={20} />
            <input placeholder="Search candidates, jobs..." className="w-full min-w-0 bg-transparent text-[15px] outline-none" />
          </label>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" aria-label="Notifications" className="relative">
              <Bell size={21} />
              <span className="absolute top-2 right-2 size-1.5 rounded-full bg-destructive" />
            </Button>
            <Button variant="ghost" size="icon" aria-label="Settings" onClick={() => navigate("/profile")}>
              <Settings size={22} />
            </Button>
            <button
              className="grid size-[38px] place-items-center rounded-full border-2 border-white bg-gradient-to-br from-navy to-primary text-xs font-extrabold text-white shadow-[0_0_0_1px_theme(colors.border)]"
              aria-label="Profile"
              onClick={() => navigate("/profile")}
            >
              {initials}
            </button>
          </div>
        </header>

        <div className="mx-auto my-7 w-[min(1160px,calc(100%-60px))]">
          <Outlet />
        </div>
      </section>
    </main>
  );
}
