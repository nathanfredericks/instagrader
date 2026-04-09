import Link from "next/link";
import { createServerClient } from "@/lib/api/server";
import { SiteHeader } from "@/components/site-header";
import { AssignmentStatusBadge } from "@/components/assignment-status-badge";
import { AssignmentActions } from "@/components/assignment-actions";
import { AssignmentDetail } from "@/components/assignment-detail";
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList,
  BreadcrumbPage, BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

export default async function AssignmentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const client = await createServerClient();
  const { data: assignment } = await client.GET("/api/assignments/{assignment_id}/", {
    params: { path: { assignment_id: id } },
  });

  if (!assignment) {
    return <div className="p-6">Assignment not found.</div>;
  }

  const { data: rubric } = await client.GET("/api/rubrics/{rubric_id}/", {
    params: { path: { rubric_id: assignment.rubric } },
  });

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
              <BreadcrumbPage>{assignment.title}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </SiteHeader>
      <div className="flex flex-1 flex-col gap-6 p-4 lg:p-6">
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold">{assignment.title}</h1>
              <AssignmentStatusBadge status={assignment.status} />
            </div>
            <AssignmentActions
              assignmentId={id}
              title={assignment.title}
              description={assignment.description ?? ""}
              status={assignment.status}
            />
          </div>
          <p className="text-muted-foreground text-sm">
            {rubric ? `Rubric: ${rubric.name}` : ""} · {assignment.essays.length} essay{assignment.essays.length !== 1 ? "s" : ""}
          </p>
          {assignment.description ? (
            <p className="text-muted-foreground text-sm">
              {assignment.description}
            </p>
          ) : null}
        </div>

        <AssignmentDetail
          assignmentId={id}
          initialAssignment={assignment}
          initialRubric={rubric}
        />
      </div>
    </>
  );
}
