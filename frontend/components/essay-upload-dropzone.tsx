"use client";

import { useState, useRef, useCallback, type ReactNode } from "react";
import { UploadIcon, XIcon, FileTextIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CircleAlert } from "lucide-react";
import { PUBLIC_API_URL } from "@/lib/config";
import type { EssayList } from "@/lib/types";

function FileList({
  files,
  uploading,
  onRemove,
  onUpload,
}: {
  files: File[];
  uploading: boolean;
  onRemove: (index: number) => void;
  onUpload: () => void;
}) {
  if (files.length === 0) return null;

  return (
    <div className="space-y-2">
      {files.map((file, index) => (
        <div
          key={`${file.name}-${file.lastModified}-${index}`}
          className="flex items-center justify-between rounded-md border px-3 py-2"
        >
          <div className="flex items-center gap-2">
            <FileTextIcon className="text-muted-foreground h-4 w-4" />
            <span className="text-sm">{file.name}</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={(e) => {
              e.stopPropagation();
              onRemove(index);
            }}
          >
            <XIcon className="h-3 w-3" />
          </Button>
        </div>
      ))}
      <Button onClick={onUpload} disabled={uploading} className="w-full">
        {uploading
          ? "Uploading..."
          : `Upload ${files.length} file${files.length !== 1 ? "s" : ""}`}
      </Button>
    </div>
  );
}

function DropzoneCard({
  dragOver,
  onClick,
  onDragOver,
  onDragEnter,
  onDragLeave,
  onDrop,
}: {
  dragOver: boolean;
  onClick: () => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragEnter: (e: React.DragEvent) => void;
  onDragLeave: () => void;
  onDrop: (e: React.DragEvent) => void;
}) {
  return (
    <Card
      className={`cursor-pointer border-2 border-dashed transition-colors ${
        dragOver ? "border-primary bg-muted/50" : "border-muted-foreground/25"
      }`}
      onClick={onClick}
      onDragOver={onDragOver}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <CardContent className="flex flex-col items-center justify-center py-12">
        <UploadIcon className="text-muted-foreground mb-4 h-10 w-10" />
        <p className="text-sm font-medium">
          Drop files here or click to browse
        </p>
        <p className="text-muted-foreground mt-1 text-xs">
          PDF, DOCX, TXT, or ZIP files
        </p>
      </CardContent>
    </Card>
  );
}

function useUpload({
  assignmentId,
  onUploadStart,
  onUploadSuccess,
  onUploadDeferred,
  onUploadValidationError,
}: {
  assignmentId: string;
  onUploadStart?: (files: File[]) => void;
  onUploadSuccess?: (essays: EssayList[]) => void;
  onUploadDeferred?: (message: string) => void;
  onUploadValidationError?: (message: string, files: File[]) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // deduplicates by filename, silently drops files already in the list
  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...fileArray.filter((f) => !existing.has(f.name))];
    });
    setError(null);
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // 400 means validation error (wrong file type etc), other failures trigger the reconciling state
  const handleUpload = async () => {
    if (files.length === 0) return;

    const uploadFiles = [...files];
    onUploadStart?.(uploadFiles);

    setUploading(true);
    setError(null);

    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }

    try {
      const response = await fetch(
        `${PUBLIC_API_URL}/api/assignments/${assignmentId}/upload/`,
        {
          method: "POST",
          body: formData,
          credentials: "include",
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => null);

        if (response.status === 400) {
          const message = data?.detail || "Upload failed";
          onUploadValidationError?.(message, uploadFiles);
          setError(message);
          return;
        }

        setFiles([]);
        onUploadDeferred?.(
          data?.detail ||
            "Upload request is being reconciled. Submission status will update shortly."
        );
        return;
      }

      const uploadedEssays = (await response.json().catch(() => [])) as EssayList[];
      setFiles([]);
      onUploadSuccess?.(uploadedEssays);
    } catch {
      setFiles([]);
      onUploadDeferred?.(
        "Upload request was interrupted. Checking submission status automatically."
      );
    } finally {
      setUploading(false);
    }
  };

  return {
    fileInputRef,
    files,
    uploading,
    error,
    dragOver,
    setDragOver,
    addFiles,
    removeFile,
    handleUpload,
  };
}

function HiddenFileInput({
  fileInputRef,
  addFiles,
}: {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  addFiles: (files: FileList) => void;
}) {
  return (
    <input
      ref={fileInputRef}
      type="file"
      multiple
      accept=".pdf,.docx,.txt,.zip"
      className="hidden"
      onChange={(e) => {
        if (e.target.files) {
          addFiles(e.target.files);
          e.target.value = "";
        }
      }}
    />
  );
}

export function EssayUploadDropzone({
  assignmentId,
  mode,
  children,
  onUploadStart,
  onUploadSuccess,
  onUploadDeferred,
  onUploadValidationError,
}: {
  assignmentId: string;
  mode: "full" | "overlay";
  children?: ReactNode;
  onUploadStart?: (files: File[]) => void;
  onUploadSuccess?: (essays: EssayList[]) => void;
  onUploadDeferred?: (message: string) => void;
  onUploadValidationError?: (message: string, files: File[]) => void;
}) {
  const {
    fileInputRef,
    files,
    uploading,
    error,
    dragOver,
    setDragOver,
    addFiles,
    removeFile,
    handleUpload,
  } = useUpload({
    assignmentId,
    onUploadStart,
    onUploadSuccess,
    onUploadDeferred,
    onUploadValidationError,
  });

  const dragHandlers = {
    onDragOver: (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(true);
    },
    onDragEnter: (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(true);
    },
    onDragLeave: () => setDragOver(false),
    onDrop: (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    },
  };

  if (mode === "full") {
    return (
      <div className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <DropzoneCard
          dragOver={dragOver}
          onClick={() => fileInputRef.current?.click()}
          {...dragHandlers}
        />

        <HiddenFileInput fileInputRef={fileInputRef} addFiles={addFiles} />

        <FileList
          files={files}
          uploading={uploading}
          onRemove={removeFile}
          onUpload={handleUpload}
        />
      </div>
    );
  }

  return (
    <div className="relative space-y-4" {...dragHandlers}>
      {error && (
        <Alert variant="destructive">
          <CircleAlert />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {children}

      {dragOver && (
        <div className="border-primary bg-muted/50 absolute inset-0 z-10 flex flex-col items-center justify-center rounded-lg border-2 border-dashed">
          <UploadIcon className="text-muted-foreground mb-4 h-10 w-10" />
          <p className="text-sm font-medium">Drop files to upload</p>
          <p className="text-muted-foreground mt-1 text-xs">
            PDF, DOCX, TXT, or ZIP files
          </p>
        </div>
      )}

      <HiddenFileInput fileInputRef={fileInputRef} addFiles={addFiles} />

      <FileList
        files={files}
        uploading={uploading}
        onRemove={removeFile}
        onUpload={handleUpload}
      />
    </div>
  );
}
