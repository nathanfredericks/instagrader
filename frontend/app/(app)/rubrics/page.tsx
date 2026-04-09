import Link from "next/link";
import type { Metadata } from "next";

import { createServerClient } from "@/lib/api/server";
import { RubricsTable } from "@/components/rubrics-table";
import { SiteHeader } from "@/components/site-header";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { PlusIcon } from "lucide-react";

export const metadata: Metadata = {
  title: "Rubrics",
};

export default async function RubricsPage() {
  const client = await createServerClient();
  const { data: rubrics } = await client.GET("/api/rubrics/");

  return (
    <>
      <SiteHeader>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbPage>Rubrics</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </SiteHeader>
      <div className="flex flex-1 flex-col gap-6 p-4 lg:p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Rubrics</h1>
          <Button asChild>
            <Link href="/rubrics/new">
              <PlusIcon />
              New rubric
            </Link>
          </Button>
        </div>
        <RubricsTable initialRubrics={rubrics ?? []} />
      </div>
    </>
  );
}

