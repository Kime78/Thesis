import { useState, useEffect, useMemo } from "react";
import axios from "axios"; // Import axios for download progress
import DropzoneUpload from "@/components/dropzone-upload";
import FileCard from "@/components/file";
import { title } from "@/components/primitives";
import DefaultLayout from "@/layouts/default";
import { defaultStyles } from "react-file-icon";
import { Card, CardBody } from "@heroui/card";
import { Progress } from "@heroui/progress";
import { FileIcon } from "react-file-icon";

// Define a type for our file data for type safety
type UploadedFile = {
  title: string;
  mimeType: string;
  size: string; // Formatted size for display e.g., "123.45 KB"
  rawSize: number; // Raw size in bytes, for accurate sorting
  extension: keyof typeof defaultStyles;
  file_uuid: string;
  uploadDate: string; // ISO date string, for sorting
};

type DownloadingFile = {
  fileUuid: string;
  fileName: string;
  progress: number;
  extension: keyof typeof defaultStyles;
};

// Define types for sorting for better type safety
type SortType = "title" | "rawSize" | "extension" | "uploadDate";
type SortOrder = "asc" | "desc";

export default function IndexPage() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [downloadingFiles, setDownloadingFiles] = useState<DownloadingFile[]>([]);

  // State for search and sort functionality
  const [searchTerm, setSearchTerm] = useState("");
  const [sortType, setSortType] = useState<SortType>("uploadDate");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // FIX: Updated the handler to match the props of DropzoneUpload
  // The function now accepts the object provided by the onFileUpload callback.
  const handleFileUpload = (fileData: {
    title: string;
    mimeType: string;
    size: string;
    extension: keyof typeof defaultStyles;
  }) => {
    // NOTE: The DropzoneUpload component provides a pre-formatted size string (e.g., "25.6 KB")
    // but not the raw size in bytes. The 'rawSize' property is essential for accurate sorting by size.
    // We are setting it to 0 here as a placeholder. For correct functionality,
    // the DropzoneUpload component should be modified to provide the original file size in bytes.
    const newFile: UploadedFile = {
      title: fileData.title,
      mimeType: fileData.mimeType,
      size: fileData.size,
      rawSize: 0, // Placeholder, see NOTE above.
      extension: fileData.extension,
      uploadDate: new Date().toISOString(), // Set current date for newly uploaded files
      file_uuid: `temp-uuid-${Date.now()}`, // Generate a temp UUID
    };
    setUploadedFiles((prevFiles) => [...prevFiles, newFile]);
  };

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const response = await fetch("http://172.30.6.237:8000/files");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const files = await response.json();

        const formattedFiles: UploadedFile[] = files.map((file: any) => ({
          title: file.file_name,
          mimeType: file.content_type,
          size: `${(file.file_size / 1024).toFixed(2)} KB`,
          rawSize: file.file_size, // Keep raw size for sorting
          extension:
            (file.file_name.split(".").pop()?.toLowerCase() ||
              "txt") as keyof typeof defaultStyles,
          file_uuid: file.file_uuid,
          uploadDate: file.stored_at || new Date().toISOString(),
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
      const response = await axios.post(
        "http://172.30.6.237:8000/download",
        { file_uuid: fileUuid },
        {
          responseType: "blob",
          onDownloadProgress: (progressEvent) => {
            const total = progressEvent.total || response.headers['content-length'];
            const progress = Math.round((progressEvent.loaded * 100) / (total || 1));
            setDownloadingFiles((prev) =>
              prev.map((f) =>
                f.fileUuid === fileUuid ? { ...f, progress } : f
              )
            );
          },
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

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

  const processedFiles = useMemo(() => {
    return [...uploadedFiles]
      .filter((file) =>
        file.title.toLowerCase().includes(searchTerm.toLowerCase())
      )
      .sort((a, b) => {
        const order = sortOrder === 'asc' ? 1 : -1;

        switch (sortType) {
          case 'title':
            return a.title.localeCompare(b.title) * order;
          case 'rawSize':
            return (a.rawSize - b.rawSize) * order;
          case 'extension':
            return a.extension.localeCompare(b.extension) * order;
          case 'uploadDate':
            return (new Date(a.uploadDate).getTime() - new Date(b.uploadDate).getTime()) * order;
          default:
            return 0;
        }
      });
  }, [uploadedFiles, searchTerm, sortType, sortOrder]);


  return (
    <DefaultLayout>
      <section className="flex flex-col items-center justify-center gap-14 py-8 md:py-10">
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
                        {...(defaultStyles[extension] || {})}
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

            {/* Search and Sort Controls */}
            <div className="flex flex-col sm:flex-row gap-4 p-4 bg-zinc-800 rounded-lg">
              <input
                type="text"
                placeholder="Search files by name..."
                className="flex-grow p-2 rounded bg-zinc-700 text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <div className="flex gap-4">
                <select
                  className="p-2 rounded bg-zinc-700 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={sortType}
                  onChange={(e) => setSortType(e.target.value as SortType)}
                >
                  <option value="uploadDate">Sort by Date</option>
                  <option value="title">Sort by Name</option>
                  <option value="rawSize">Sort by Size</option>
                  <option value="extension">Sort by Type</option>
                </select>
                <select
                  className="p-2 rounded bg-zinc-700 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value as SortOrder)}
                >
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </div>
            </div>

            {/* Display Processed Files */}
            {processedFiles.length > 0 ? (
              processedFiles.map((file) => (
                <FileCard
                  key={file.file_uuid}
                  title={file.title}
                  mimeType={file.mimeType}
                  size={file.size}
                  extension={file.extension}
                  storedAt={file.uploadDate}
                  onDownload={() =>
                    file.file_uuid && handleDownload(file.file_uuid, file.title)
                  }
                />
              ))
            ) : (
              <div className="text-center p-8 text-zinc-500">
                No files match your search.
              </div>
            )}
          </div>
        )}
      </section>
    </DefaultLayout>
  );
}