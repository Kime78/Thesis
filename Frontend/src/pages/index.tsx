import { useState, useEffect, useMemo, useCallback } from "react";
import axios from "axios";
import DropzoneUpload from "@/components/dropzone-upload";
import FileCard from "@/components/file";
import { title } from "@/components/primitives";
import DefaultLayout from "@/layouts/default";
import { defaultStyles } from "react-file-icon";
import { Card, CardBody } from "@heroui/card";
import { Progress } from "@heroui/progress";
import { FileIcon } from "react-file-icon";

type UploadedFile = {
  title: string;
  mimeType: string;
  size: string;
  rawSize: number;
  extension: keyof typeof defaultStyles;
  file_uuid: string;
  uploadDate: string;
  status?: "uploading" | "complete";
  progress?: number;
};

type DownloadingFile = {
  fileUuid: string;
  fileName: string;
  progress: number;
  extension: keyof typeof defaultStyles;
};

type FileStatusResponse = {
  status: "uploading" | "complete";
  message: string;
  current_chunks?: number;
  expected_chunks?: number;
};

type SortType = "title" | "rawSize" | "extension" | "uploadDate";
type SortOrder = "asc" | "desc";

const API_BASE_URL = "http://172.30.6.209:8000";

export default function IndexPage() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [downloadingFiles, setDownloadingFiles] = useState<DownloadingFile[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortType, setSortType] = useState<SortType>("uploadDate");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const fetchFilesAndStatuses = useCallback(async () => {
    try {
      const filesResponse = await fetch(`${API_BASE_URL}/files`);
      if (!filesResponse.ok) {
        throw new Error(`HTTP error! status: ${filesResponse.status}`);
      }
      const files: any[] = await filesResponse.json();

      const statusPromises = files.map((file) =>
        fetch(`${API_BASE_URL}/status/${file.file_uuid}`).then((res) => res.json())
      );
      const statuses: FileStatusResponse[] = await Promise.all(statusPromises);

      const statusMap = new Map<string, FileStatusResponse>();
      statuses.forEach((status, index) => {
        statusMap.set(files[index].file_uuid, status);
      });

      const formattedFiles: UploadedFile[] = files.map((file: any) => {
        const status = statusMap.get(file.file_uuid);
        let progress = 0;
        if (status?.status === "uploading" && status.expected_chunks && status.current_chunks) {
          progress = Math.round((status.current_chunks * 100) / status.expected_chunks);
        } else if (status?.status === "complete") {
          progress = 100;
        }

        return {
          title: file.file_name,
          mimeType: file.content_type,
          size: `${(file.file_size / 1024).toFixed(2)} KB`,
          rawSize: file.file_size,
          extension:
            (file.file_name.split(".").pop()?.toLowerCase() || "txt") as keyof typeof defaultStyles,
          file_uuid: file.file_uuid,
          uploadDate: file.stored_at || new Date().toISOString(),
          status: status?.status,
          progress: progress,
        };
      });

      setUploadedFiles(formattedFiles);
    } catch (error) {
      console.error("Error fetching files and statuses:", error);
    }
  }, []);

  useEffect(() => {
    fetchFilesAndStatuses();
    const intervalId = setInterval(fetchFilesAndStatuses, 3000);

    return () => clearInterval(intervalId);
  }, [fetchFilesAndStatuses]);

  const handleFileUpload = () => {
    setTimeout(fetchFilesAndStatuses, 1000);
  };

  const handleDownload = async (fileUuid: string, fileName: string) => {
    const fileExtension =
      (fileName.split(".").pop()?.toLowerCase() || "txt") as keyof typeof defaultStyles;
    setDownloadingFiles((prev) => [
      ...prev,
      { fileUuid, fileName, progress: 0, extension: fileExtension },
    ]);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/download`,
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

      setDownloadingFiles((prev) => prev.filter((f) => f.fileUuid !== fileUuid));
    } catch (error) {
      console.error(`Error downloading ${fileName}:`, error);
      alert(`Failed to download ${fileName}. Please try again.`);
      setDownloadingFiles((prev) => prev.filter((f) => f.fileUuid !== fileUuid));
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

  const handleDelete = async (file_uuid: string): Promise<void> => {
    if (!window.confirm("Are you sure you want to delete this file? This action cannot be undone.")) {
      return;
    }

    try { 
      const response = await fetch(`${API_BASE_URL}/files/${file_uuid}`, {
        method: "DELETE",
      });
      console.log(response)
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      // Update the state to remove the file from the UI
      setUploadedFiles((currentFiles) =>
        currentFiles.filter((file) => file.file_uuid !== file_uuid)
      );

    } catch (error) {
      console.error("Failed to delete file:", error);
      alert(`An error occurred while deleting the file. Please try again. \n${error}`);
    }
  };
  return (
    <DefaultLayout>
      <section className="flex flex-col items-center justify-center gap-14 py-8 md:py-10">
        <h1 className={title()}>Upload Files</h1>
        <DropzoneUpload onFileUpload={handleFileUpload} />

        {downloadingFiles.length > 0 && (
          <div className="w-full max-w-xl mt-8 space-y-4">
            <h2 className="text-xl font-semibold text-left w-full">Downloading Files</h2>
            {downloadingFiles.map(({ fileUuid, fileName, progress, extension }) => (
              <Card key={fileUuid} className="bg-zinc-800">
                <CardBody>
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 flex-shrink-0">
                      <FileIcon extension={extension} {...(defaultStyles[extension] || {})} />
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between mb-1">
                        <p className="text-sm font-medium text-white truncate pr-4">{fileName}</p>
                        <p className="text-sm font-medium text-zinc-400">{progress}%</p>
                      </div>
                      <Progress value={progress} />
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}

        {uploadedFiles.length > 0 && (
          <div className="w-full max-w-xl mt-8 space-y-4">
            <h2 className="text-xl font-semibold text-left w-full">Uploaded Files</h2>

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

            {processedFiles.length > 0 ? (
              processedFiles.map((file) => (
                <div key={file.file_uuid}>
                  <FileCard
                    title={file.title}
                    mimeType={file.mimeType}
                    size={file.size}
                    extension={file.extension}
                    storedAt={file.uploadDate}
                    onDownload={() =>
                      file.file_uuid && file.status === "complete" && handleDownload(file.file_uuid, file.title)
                    }
                    onDelete={() => file.file_uuid && handleDelete(file.file_uuid)}
                    uploading={file.status !== "complete"}
                  />
                  {file.status === 'uploading' && (
                    <div className="bg-zinc-800 -mt-2 rounded-b-lg px-4 pb-3">
                      <Progress value={file.progress} className="w-full" />
                      <p className="text-xs text-center text-zinc-400 mt-1">Uploading... {file.progress}%</p>
                    </div>
                  )}
                </div>
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