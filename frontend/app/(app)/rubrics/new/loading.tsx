import Link from "next/link";
import { PlusIcon } from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";

export default function NewRubricLoading() {
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
        <div className="max-w-5xl space-y-6">
          <FieldGroup>
            <Field>
              <FieldLabel>Rubric name</FieldLabel>
              <Skeleton className="h-9 w-full" />
            </Field>
            <Field>
              <FieldLabel>
                Description{" "}
                <span className="text-muted-foreground font-normal">
                  (optional)
                </span>
              </FieldLabel>
              <Skeleton className="h-20 w-full" />
            </Field>
          </FieldGroup>

          <p className="text-base font-semibold text-foreground">Templates</p>

          <div className="grid gap-4 md:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-5 w-20 shrink-0" />
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-3 w-28" />
                </CardContent>
              </Card>
            ))}
          </div>

          <Button disabled>
            <PlusIcon />
            Create rubric
          </Button>
        </div>
      </div>
    </>
  );
}
