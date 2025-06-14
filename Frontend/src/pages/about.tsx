import { useState, useEffect } from "react";
import axios from "axios"; // Import axios for download progress
import DropzoneUpload from "@/components/dropzone-upload";
import FileCard from "@/components/file";
import { title } from "@/components/primitives";
import DefaultLayout from "@/layouts/default";
import { defaultStyles } from "react-file-icon";
import { Card, CardBody } from "@heroui/card"; // Assuming these are from your UI library
import { Progress } from "@heroui/progress"; // Assuming these are from your UI library
import { FileIcon } from "react-file-icon"; // For displaying file icons in download progress

// Define a type for our file data for type safety
type UploadedFile = {
  title: string;
  mimeType: string;
  size: string;
  extension: keyof typeof defaultStyles;
  file_uuid: string; // file_uuid is now required for downloaded files
};

type DownloadingFile = {
  fileUuid: string;
  fileName: string;
  progress: number;
  // Add an extension for the FileIcon in the progress card
  extension: keyof typeof defaultStyles;
};

export default function DocsPage() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [downloadingFiles, setDownloadingFiles] = useState<DownloadingFile[]>(
    []
  );

  const handleFileUpload = (file: Omit<UploadedFile, 'file_uuid'> & { file_uuid?: string }) => {
    setUploadedFiles((prevFiles) => [
      ...prevFiles,
      { ...file, file_uuid: file.file_uuid || `temp-uuid-${Date.now()}` }
    ]);
  };

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const response = await fetch("http://localhost:7000/files");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const files = await response.json();

        const formattedFiles: UploadedFile[] = files.map((file: any) => ({
          title: file.file_name,
          mimeType: file.content_type,
          size: `${(file.file_size / 1024).toFixed(2)} KB`,
          extension:
            (file.file_name.split(".").pop()?.toLowerCase() ||
              "txt") as keyof typeof defaultStyles,
          file_uuid: file.file_uuid,
        }));
        setUploadedFiles(formattedFiles);
      } catch (error) {
        console.error("Error fetching files:", error);
      }
    };

    fetchFiles();
  }, []);

  const handleDownload = async (fileUuid: string, fileName: string) => {
    const fileExtension =
      (fileName.split(".").pop()?.toLowerCase() ||
        "txt") as keyof typeof defaultStyles;
    setDownloadingFiles((prev) => [
      ...prev,
      { fileUuid, fileName, progress: 0, extension: fileExtension },
    ]);

    try {
      // Corrected to a POST request with file_uuid in the request body
      const response = await axios.post(
        "http://localhost:7000/download", // Endpoint remains the same
        { file_uuid: fileUuid }, // Send file_uuid in the request body
        {
          responseType: "blob", // Important for downloading files
          onDownloadProgress: (progressEvent) => {
            const progress = Math.round(
              (progressEvent.loaded * 100) / (progressEvent.total || 1)
            );
            setDownloadingFiles((prev) =>
              prev.map((f) =>
                f.fileUuid === fileUuid ? { ...f, progress } : f
              )
            );
          },
        }
      );

      // Create a URL for the blob and trigger a download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();

      setDownloadingFiles((prev) =>
        prev.filter((f) => f.fileUuid !== fileUuid)
      );
    } catch (error) {
      console.error(`Error downloading ${fileName}:`, error);
      alert(`Failed to download ${fileName}. Please try again.`);
      setDownloadingFiles((prev) =>
        prev.filter((f) => f.fileUuid !== fileUuid)
      );
    }
  };

  return (
    <DefaultLayout>
      <section className="flex flex-col items-center justify-center gap-4 py-8 md:py-10">
        <h1 className={title()}>Upload Files</h1>

        <DropzoneUpload onFileUpload={handleFileUpload} />

        {/* Render download progress */}
        {downloadingFiles.length > 0 && (
          <div className="w-full max-w-xl mt-8 space-y-4">
            <h2 className="text-xl font-semibold text-left w-full">
              Downloading Files
            </h2>
            {downloadingFiles.map(({ fileUuid, fileName, progress, extension }) => (
              <Card key={fileUuid} className="bg-zinc-800">
                <CardBody>
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10">
                      <FileIcon
                        extension={extension}
                        {...(defaultStyles[
                          extension as keyof typeof defaultStyles
                        ] || {})}
                      />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{fileName}</p>
                      <Progress value={progress} className="mt-1" />
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}

        {/* Render the list of uploaded files dynamically */}
        {uploadedFiles.length > 0 && (
          <div className="w-full max-w-xl mt-8 space-y-4">
            <h2 className="text-xl font-semibold text-left w-full">
              Uploaded Files
            </h2>
            {uploadedFiles.map((file) => (
              <FileCard
                key={file.file_uuid}
                title={file.title}
                mimeType={file.mimeType}
                size={file.size}
                extension={file.extension}
                onDownload={() =>
                  file.file_uuid && handleDownload(file.file_uuid, file.title)
                }
              />
            ))}
          </div>
        )}
      </section>
    </DefaultLayout>
  );
}