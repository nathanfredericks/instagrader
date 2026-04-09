"use client";

import { useCallback, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { Card, CardAction, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Download } from "lucide-react";
import { PUBLIC_API_URL } from "@/lib/config";

interface EssayTextPanelProps {
  extractedText: string;
  assignmentId: string;
  essayId: string;
}

export function EssayTextPanel({
  extractedText,
  assignmentId,
  essayId,
}: EssayTextPanelProps) {
  const wordCount = useMemo(
    () => extractedText.trim().split(/\s+/).filter(Boolean).length,
    [extractedText]
  );
  const charCount = useMemo(() => extractedText.length, [extractedText]);

  const handleDownload = useCallback(async () => {
    const response = await fetch(
      `${PUBLIC_API_URL}/api/assignments/${assignmentId}/export/pdf/${essayId}/`,
      { credentials: "include" }
    );
    if (!response.ok) return;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "essay";
    a.click();
    URL.revokeObjectURL(url);
  }, [assignmentId, essayId]);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <CardTitle>Essay</CardTitle>
        <CardAction>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleDownload}
                aria-label="Download original essay file"
              >
                <Download className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Download original</TooltipContent>
          </Tooltip>
        </CardAction>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto">
        <div className="text-sm leading-relaxed [&_p]:my-3 [&_ul]:my-3 [&_ol]:my-3 [&_li]:my-1 [&_h1]:text-xl [&_h1]:font-semibold [&_h2]:text-lg [&_h2]:font-semibold [&_h3]:text-base [&_h3]:font-semibold">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeSanitize]}
          >
            {extractedText}
          </ReactMarkdown>
        </div>
      </CardContent>
      <CardFooter className="border-t text-[11px] tracking-widest text-muted-foreground uppercase tabular-nums">
        <span><span className="font-semibold text-foreground/70">{wordCount}</span> words</span>
        <span className="mx-3 text-border">·</span>
        <span><span className="font-semibold text-foreground/70">{charCount}</span> characters</span>
      </CardFooter>
    </Card>
  );
}
