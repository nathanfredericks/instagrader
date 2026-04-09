import Link from "next/link";
import type { Metadata } from "next";

import { createServerClient } from "@/lib/api/server";
import { RubricTemplateSelector } from "@/components/rubric-template-selector";
import { SiteHeader } from "@/components/site-header";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

export const metadata: Metadata = {
  title: "New Rubric",
};

export default async function NewRubricPage() {
  const client = await createServerClient();
  const { data: templates } = await client.GET("/api/rubrics/templates/");

  return (
    <>
      <SiteHeader>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link href="/rubrics">Rubrics</Link>
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
        <h1 className="text-2xl font-semibold">Create rubric</h1>
        <RubricTemplateSelector initialTemplates={templates ?? []} />
      </div>
    </>
  );
}

