import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

import { createServerClient } from "@/lib/api/server";
import { RubricDesigner } from "@/components/rubric-designer";
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
  title: "Rubric Designer",
};

export default async function RubricDesignerPage({
  params,
}: {
  params: Promise<{ rubricId: string }>;
}) {
  const { rubricId } = await params;
  const client = await createServerClient();
  const { data: rubric, response } = await client.GET("/api/rubrics/{rubric_id}/", {
    params: { path: { rubric_id: rubricId } },
  });

  if (!response.ok || !rubric) {
    notFound();
  }

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
              <BreadcrumbPage>{rubric.name}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </SiteHeader>
      <div className="flex flex-1 flex-col gap-6 p-4 lg:p-6 min-w-0">
        <RubricDesigner initialRubric={rubric} />
      </div>
    </>
  );
}
