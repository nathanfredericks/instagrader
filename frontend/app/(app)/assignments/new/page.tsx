import Link from "next/link";
import { createServerClient } from "@/lib/api/server";
import { SiteHeader } from "@/components/site-header";
import { NewAssignmentContent } from "@/components/new-assignment-content";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "New Assignment",
};

export default async function NewAssignmentPage() {
  const client = await createServerClient();
  const { data: rubrics } = await client.GET("/api/rubrics/");

  return (
    <>
      <SiteHeader>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link href="/assignments">Assignments</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>New</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </SiteHeader>
      <div className="flex flex-1 flex-col gap-6 p-4 lg:p-6">
        <h1 className="text-2xl font-semibold">Create assignment</h1>
        <NewAssignmentContent initialRubrics={rubrics ?? []} />
      </div>
    </>
  );
}
