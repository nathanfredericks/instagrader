import { cookies } from "next/headers"
import { redirect } from "next/navigation"
import { getCurrentUser } from "@/lib/auth"
import { AppSidebar } from "@/components/app-sidebar"
import { SessionWatcher } from "@/components/session-watcher"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const cookieStore = await cookies()
  // presence-only check, actual token validation happens in proxy.ts
  if (!cookieStore.get("access_token")?.value) {
    redirect("/login")
  }

  const user = await getCurrentUser()

  return (
    <TooltipProvider>
      <SidebarProvider
        style={
          {
            "--sidebar-width": "calc(var(--spacing) * 72)",
            "--header-height": "calc(var(--spacing) * 12)",
          } as React.CSSProperties
        }
      >
        <AppSidebar user={{ full_name: user?.full_name ?? "", email: user?.email ?? "" }} />
        <SidebarInset>
          <SessionWatcher />
          {children}
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
