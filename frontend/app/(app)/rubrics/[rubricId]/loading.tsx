import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Card, CardHeader } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";

export default function RubricDesignerLoading() {
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
              <Skeleton className="h-4 w-32" />
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </SiteHeader>
      <div className="flex flex-1 flex-col gap-6 p-4 lg:p-6 min-w-0">
        <div className="space-y-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <Skeleton className="h-8 w-48" />
              <Skeleton className="mt-1 h-4 w-40" />
            </div>
            <Skeleton className="h-9 w-9 shrink-0" />
          </div>

          <FieldGroup>
            <Field>
              <FieldLabel>Name</FieldLabel>
              <Skeleton className="h-9 w-full" />
            </Field>
            <Field>
              <FieldLabel>
                Description{" "}
                <span className="text-muted-foreground font-normal">
                  (optional)
                </span>
              </FieldLabel>
              <Skeleton className="h-16 w-full" />
            </Field>
          </FieldGroup>

          {/* Desktop criteria table */}
          <div className="hidden lg:block rounded-lg border">
            <div className="flex bg-muted/40 border-b text-sm font-medium">
              <div className="min-w-[220px] w-[260px] shrink-0 p-3 border-r">Criterion</div>
              <div className="flex-1 p-3">Levels</div>
            </div>
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex border-b last:border-b-0">
                <div className="min-w-[220px] w-[260px] shrink-0 p-3 border-r flex items-center">
                  <Skeleton className="h-9 w-full" />
                </div>
                <div className="flex-1 p-3 flex gap-3">
                  {Array.from({ length: 3 }).map((_, j) => (
                    <Skeleton key={j} className="h-20 w-44 shrink-0" />
                  ))}
                </div>
              </div>
            ))}
            <div className="border-t p-3">
              <Skeleton className="h-9 w-9" />
            </div>
          </div>

          {/* Mobile criteria cards */}
          <div className="lg:hidden space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardHeader className="flex flex-row items-center gap-2 space-y-0">
                  <Skeleton className="h-9 flex-1" />
                  <Skeleton className="h-8 w-8 shrink-0" />
                  <Skeleton className="h-8 w-8 shrink-0" />
                </CardHeader>
              </Card>
            ))}
          </div>
          <div className="lg:hidden">
            <Skeleton className="h-9 w-32" />
          </div>

          <div className="border-t pt-4">
            <Skeleton className="h-9 w-28" />
          </div>
        </div>
      </div>
    </>
  );
}
