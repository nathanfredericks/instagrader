"use client"

import * as React from "react"
import Link from "next/link"

import { NavMain } from "@/components/nav-main"
import { NavUser } from "@/components/nav-user"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import {
  FileTextIcon,
  GraduationCapIcon,
  LayoutDashboardIcon,
  ListChecksIcon,
} from "lucide-react"

const navItems: React.ComponentProps<typeof NavMain>["items"] = [
  {
    title: "Dashboard",
    url: "/",
    icon: <LayoutDashboardIcon />,
  },
  {
    title: "Assignments",
    url: "/assignments",
    icon: <FileTextIcon />,
  },
  {
    title: "Rubrics",
    url: "/rubrics",
    icon: <ListChecksIcon />,
  },
]

export function AppSidebar({
  user,
  ...props
}: { user: { full_name: string; email: string } } & React.ComponentProps<
  typeof Sidebar
>) {
  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:p-1.5!"
            >
              <Link href="/">
                <GraduationCapIcon className="size-5!" />
                <span className="text-base font-semibold">InstaGrader</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={navItems} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={user} />
      </SidebarFooter>
    </Sidebar>
  )
}
