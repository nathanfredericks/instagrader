import { createServerClient } from "@/lib/api/server";
import { SiteHeader } from "@/components/site-header";
import { DashboardContent } from "@/components/dashboard-content";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default async function DashboardPage() {
  const client = await createServerClient();
  const { data: dashboard } = await client.GET("/api/dashboard/");

  if (!dashboard) {
    return null;
  }

  return (
    <>
      <SiteHeader>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbPage>Dashboard</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </SiteHeader>
      <div className="flex flex-1 flex-col gap-6 p-4 lg:p-6">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <DashboardContent initialData={dashboard} />
      </div>
    </>
  );
}
