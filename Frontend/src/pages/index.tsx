import React, { useState, useEffect, useMemo, useCallback, FC } from "react";
import axios from "axios";

// --- Mock Components for Standalone Running ---
// In a real app, you would use your actual component libraries.

const Card: FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <div className={`bg-zinc-900 rounded-lg shadow-md ${className}`}>{children}</div>
);
const CardBody: FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="p-4">{children}</div>
);
const Progress: FC<{ value?: number; className?: string }> = ({ value = 0, className }) => (
  <div className={`w-full bg-zinc-700 rounded-full h-2.5 ${className}`}>
    <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${value}%` }}></div>
  </div>
);
const Button: FC<{ children: React.ReactNode; onPress?: () => void; className?: string; "aria-label"?: string; isDisabled?: boolean; variant?: string; color?: string, startContent?: React.ReactNode }> = ({ children, onPress, className, isDisabled, startContent }) => (
  <button onClick={onPress} disabled={isDisabled} className={`flex items-center gap-2 px-4 py-2 rounded-md font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-zinc-900 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}>
    {startContent}
    {children}
  </button>
);
const FileIcon: FC<{ extension: string }> = ({ extension }) => (
  <div className="w-full h-full flex items-center justify-center bg-gray-500 rounded-md text-white font-bold text-xs uppercase p-1">
    {extension}
  </div>
);
const DropzoneUpload: FC<{ onFileUpload: () => void }> = ({ onFileUpload }) => {
  const handleSimulatedUpload = () => {
    console.log("Simulating file upload...");
    onFileUpload();
  };
  return (
    <div className="w-full max-w-xl border-2 border-dashed border-zinc-600 rounded-lg p-10 text-center text-zinc-400">
      <p>Dropzone Area</p>
      <p className="text-sm">In a real app, this would be your file dropzone component.</p>
      <button onClick={handleSimulatedUpload} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded">Simulate Upload</button>
    </div>
  );
};
const DefaultLayout: FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="bg-zinc-950 text-white min-h-screen font-sans">{children}</div>
);
const title = () => "text-4xl font-bold tracking-tight";
const Download: FC<{ size: number }> = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>;
const Trash2: FC<{ size: number }> = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" /></svg>;


// --- Helper Types ---

type UploadedFile = {
  title: string;
  mimeType: string;
  size: string;
  rawSize: number;
  extension: string;
  file_uuid: string;
  uploadDate: string;
  status?: "uploading" | "complete";
  progress?: number;
};

type DownloadingFile = {
  fileUuid: string;
  fileName: string;
  progress: number;
  extension: string;
};

type FileStatusResponse = {
  status: "uploading" | "complete";
  message: string;
  current_chunks?: number;
  expected_chunks?: number;
};

type SortType = "title" | "rawSize" | "extension" | "uploadDate";
type SortOrder = "asc" | "desc";

type NotificationType = {
  message: string;
  type: 'success' | 'error';
};

type ConfirmationType = {
  message: string;
  onConfirm: () => void;
};


const API_BASE_URL = "http://172.30.6.209:8000";


// --- Reusable Components ---

const FileCard: FC<{
  title: string;
  size: string;
  storedAt: string;
  extension: string;
  onDownload?: () => void;
  onDelete?: () => void;
  isDownloadDisabled?: boolean;
}> = ({ title, size, storedAt, extension, onDownload, onDelete, isDownloadDisabled }) => {
  const formattedStoredAt = new Date(storedAt).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <Card className="max-w-xl w-full">
      <CardBody>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-1 min-w-0">
            <div className="flex-shrink-0 w-12 h-12">
              <FileIcon extension={extension} />
            </div>
            <div className="flex flex-col justify-center text-left min-w-0">
              <h2 className="text-base font-semibold truncate text-white" title={title}>
                {title}
              </h2>
              <p className="text-sm text-gray-400">{formattedStoredAt}</p>
              <p className="text-sm text-gray-500">{size}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Button
              onPress={onDownload}
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="Download file"
              isDisabled={isDownloadDisabled}
            >
              <Download size={20} />
            </Button>
            <Button
              onPress={onDelete}
              className="text-red-500 hover:text-red-400 transition-colors"
              aria-label="Delete file"
            >
              <Trash2 size={20} />
            </Button>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

const ConfirmationModal: FC<{
  confirmation: ConfirmationType | null;
  onClose: () => void;
}> = ({ confirmation, onClose }) => {
  if (!confirmation) return null;

  const handleConfirm = () => {
    confirmation.onConfirm();
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex justify-center items-center z-50 transition-opacity">
      <div className="bg-zinc-800 p-6 rounded-lg shadow-xl w-full max-w-md mx-4">
        <p className="text-lg text-white mb-6">{confirmation.message}</p>
        <div className="flex justify-end gap-4">
          <Button variant="light" className="bg-zinc-700 hover:bg-zinc-600" onPress={onClose}>Cancel</Button>
          <Button color="danger" className="bg-red-600 hover:bg-red-700" onPress={handleConfirm}>Confirm</Button>
        </div>
      </div>
    </div>
  );
};

const Notification: FC<{
  notification: NotificationType | null;
  onDismiss: () => void;
}> = ({ notification, onDismiss }) => {
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => {
        onDismiss();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [notification, onDismiss]);

  if (!notification) return null;

  const baseClasses = "fixed bottom-5 right-5 z-50 p-4 rounded-lg shadow-xl text-white font-semibold transition-transform transform translate-y-0 opacity-100";
  const typeClasses = notification.type === 'error' ? 'bg-red-600' : 'bg-green-600';

  return (
    <div className={`${baseClasses} ${typeClasses}`} onClick={onDismiss} style={{ cursor: 'pointer' }}>
      {notification.message}
    </div>
  );
};


// --- Main Application Page ---

function App() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [downloadingFiles, setDownloadingFiles] = useState<DownloadingFile[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortType, setSortType] = useState<SortType>("uploadDate");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [notification, setNotification] = useState<NotificationType | null>(null);
  const [confirmation, setConfirmation] = useState<ConfirmationType | null>(null);

  const fetchFilesAndStatuses = useCallback(async () => {
    try {
      const filesResponse = await fetch(`${API_BASE_URL}/files`);
      if (!filesResponse.ok) throw new Error(`HTTP error! status: ${filesResponse.status}`);
      const files: any[] = await filesResponse.json();

      const statusPromises = files.map((file) =>
        fetch(`${API_BASE_URL}/status/${file.file_uuid}`).then((res) => res.json())
      );
      const statuses: FileStatusResponse[] = await Promise.all(statusPromises);
      const statusMap = new Map(files.map((file, index) => [file.file_uuid, statuses[index]]));

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
          extension: (file.file_name.split(".").pop()?.toLowerCase() || "txt"),
          file_uuid: file.file_uuid,
          uploadDate: file.stored_at || new Date().toISOString(),
          status: status?.status,
          progress: progress,
        };
      });
      setUploadedFiles(formattedFiles);
    } catch (error) {
      console.error("Error fetching files and statuses:", error);
      setNotification({ message: "Could not fetch file list.", type: "error" });
    }
  }, []);

  useEffect(() => {
    fetchFilesAndStatuses();
    const intervalId = setInterval(fetchFilesAndStatuses, 5000);
    return () => clearInterval(intervalId);
  }, [fetchFilesAndStatuses]);

  const handleFileUpload = () => {
    setTimeout(fetchFilesAndStatuses, 1000);
  };

  const handleDownload = async (fileUuid: string, fileName: string) => {
    const fileExtension = (fileName.split(".").pop()?.toLowerCase() || "txt");
    setDownloadingFiles((prev) => [...prev, { fileUuid, fileName, progress: 0, extension: fileExtension }]);
    try {
      const response = await axios.post(`${API_BASE_URL}/download`, { file_uuid: fileUuid }, {
        responseType: "blob",
        onDownloadProgress: (progressEvent) => {
          const total = progressEvent.total || Number(response.headers['content-length']);
          const progress = Math.round((progressEvent.loaded * 100) / (total || 1));
          setDownloadingFiles((prev) => prev.map((f) => (f.fileUuid === fileUuid ? { ...f, progress } : f)));
        },
      });
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
      setNotification({ message: `Failed to download ${fileName}.`, type: 'error' });
      setDownloadingFiles((prev) => prev.filter((f) => f.fileUuid !== fileUuid));
    }
  };

  const handleDelete = (fileUuid: string, fileName: string) => {
    setConfirmation({
      message: `Are you sure you want to delete ${fileName}? This action cannot be undone.`,
      onConfirm: async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/files/${fileUuid}`, { method: 'DELETE' });
          if (!response.ok) throw new Error('Server responded with an error.');
          setUploadedFiles((prev) => prev.filter((file) => file.file_uuid !== fileUuid));
          setNotification({ message: `${fileName} has been deleted.`, type: 'success' });
        } catch (error) {
          console.error(`Error deleting ${fileName}:`, error);
          setNotification({ message: `Failed to delete ${fileName}.`, type: 'error' });
        }
      }
    });
  };

  const handleDeleteAll = () => {
    setConfirmation({
      message: "Are you sure you want to delete ALL files? This is a permanent action.",
      onConfirm: async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/files`, { method: 'DELETE' });
          if (!response.ok) throw new Error('Server responded with an error.');
          setUploadedFiles([]);
          setNotification({ message: "All files have been deleted.", type: 'success' });
        } catch (error) {
          console.error("Error deleting all files:", error);
          setNotification({ message: "Failed to delete all files.", type: 'error' });
        }
      }
    });
  };

  const processedFiles = useMemo(() => {
    return [...uploadedFiles]
      .filter((file) => file.title.toLowerCase().includes(searchTerm.toLowerCase()))
      .sort((a, b) => {
        const order = sortOrder === 'asc' ? 1 : -1;
        if (sortType === 'uploadDate') {
          return (new Date(a.uploadDate).getTime() - new Date(b.uploadDate).getTime()) * order;
        }
        const aVal = a[sortType];
        const bVal = b[sortType];
        if (typeof aVal === 'string' && typeof bVal === 'string') return aVal.localeCompare(bVal) * order;
        if (typeof aVal === 'number' && typeof bVal === 'number') return (aVal - bVal) * order;
        return 0;
      });
  }, [uploadedFiles, searchTerm, sortType, sortOrder]);

  return (
    <DefaultLayout>
      <Notification notification={notification} onDismiss={() => setNotification(null)} />
      <ConfirmationModal confirmation={confirmation} onClose={() => setConfirmation(null)} />
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
                      <FileIcon extension={extension} />
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
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold text-left">Uploaded Files</h2>
              <Button
                variant="light"
                className="text-red-500 hover:bg-red-500/10"
                onPress={handleDeleteAll}
                startContent={<Trash2 size={16} />}
              >
                Delete All
              </Button>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 p-4 bg-zinc-800 rounded-lg">
              <input type="text" placeholder="Search files by name..." className="flex-grow p-2 rounded bg-zinc-700 text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
              <div className="flex gap-4">
                <select className="p-2 rounded bg-zinc-700 text-white focus:outline-none focus:ring-2 focus:ring-blue-500" value={sortType} onChange={(e) => setSortType(e.target.value as SortType)}>
                  <option value="uploadDate">Sort by Date</option>
                  <option value="title">Sort by Name</option>
                  <option value="rawSize">Sort by Size</option>
                  <option value="extension">Sort by Type</option>
                </select>
                <select className="p-2 rounded bg-zinc-700 text-white focus:outline-none focus:ring-2 focus:ring-blue-500" value={sortOrder} onChange={(e) => setSortOrder(e.target.value as SortOrder)}>
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
                    onDownload={() => file.file_uuid && file.status === "complete" && handleDownload(file.file_uuid, file.title)}
                    onDelete={() => handleDelete(file.file_uuid, file.title)}
                    isDownloadDisabled={file.status !== "complete"}
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
              <div className="text-center p-8 text-zinc-500 bg-zinc-800 rounded-lg">
                No files match your search.
              </div>
            )}
          </div>
        )}
      </section>
    </DefaultLayout>
  );
}

export default App;
