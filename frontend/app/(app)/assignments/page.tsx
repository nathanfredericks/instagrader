import Link from "next/link";
import { createServerClient } from "@/lib/api/server";
import { SiteHeader } from "@/components/site-header";
import { AssignmentsTable } from "@/components/assignments-table";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { PlusIcon } from "lucide-react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Assignments",
};

export default async function AssignmentsPage() {
  const client = await createServerClient();
  const { data: assignments } = await client.GET("/api/assignments/");

  return (
    <>
      <SiteHeader>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbPage>Assignments</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </SiteHeader>
      <div className="flex flex-1 flex-col gap-6 p-4 lg:p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Assignments</h1>
          <Button asChild>
            <Link href="/assignments/new">
              <PlusIcon />
              New assignment
            </Link>
          </Button>
        </div>
        <AssignmentsTable initialAssignments={assignments ?? []} />
      </div>
    </>
  );
}
