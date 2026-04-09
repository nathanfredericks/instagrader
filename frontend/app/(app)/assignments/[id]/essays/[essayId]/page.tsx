import Link from "next/link";
import { createServerClient } from "@/lib/api/server";
import { SiteHeader } from "@/components/site-header";
import { AssignmentEssayReview } from "@/components/assignment-essay-review";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

export default async function AssignmentEssayReviewPage({
  params,
}: {
  params: Promise<{ id: string; essayId: string }>;
}) {
  const { id, essayId } = await params;
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

  // parallel fetch, essay data and grading result loaded concurrently
  const [essayRes, gradingRes] = await Promise.all([
    client.GET("/api/essays/{essay_id}/", {
      params: { path: { essay_id: essayId } },
    }),
    client.GET("/api/essays/{essay_id}/grading/", {
      params: { path: { essay_id: essayId } },
    }),
  ]);

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
              <BreadcrumbLink asChild>
                <Link href={`/assignments/${id}`}>{assignment.title}</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{essayRes.data?.file_name ?? "Essay Review"}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </SiteHeader>

      <div className="flex flex-1 flex-col gap-6 p-4 lg:p-6">
        <AssignmentEssayReview
          assignmentId={id}
          essayId={essayId}
          initialAssignment={assignment}
          initialRubric={rubric}
          initialEssay={essayRes.data}
          initialGrading={gradingRes.data}
        />
      </div>
    </>
  );
}
