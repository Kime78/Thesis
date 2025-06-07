import { useState } from "react";
import DropzoneUpload from "@/components/dropzone-upload";
import FileCard from "@/components/file";
import { title } from "@/components/primitives";
import DefaultLayout from "@/layouts/default";
import type { defaultStyles } from "react-file-icon";

// Define a type for our file data for type safety
type UploadedFile = {
  title: string;
  mimeType: string;
  size: string;
  extension: keyof typeof defaultStyles;
};

export default function DocsPage() {
  // State to hold the list of successfully uploaded files
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  // Function to add a new file to the state
  const handleFileUpload = (file: UploadedFile) => {
    setUploadedFiles((prevFiles) => [...prevFiles, file]);
  };

  return (
    <DefaultLayout>
      <section className="flex flex-col items-center justify-center gap-4 py-8 md:py-10">
        <h1 className={title()}>Upload Files</h1>

        {/* Pass the handler function as a prop to the dropzone */}
        <DropzoneUpload onFileUpload={handleFileUpload} />

        {/* Render the list of uploaded files dynamically */}
        {uploadedFiles.length > 0 && (
          <div className="w-full max-w-xl mt-8 space-y-4">
            <h2 className="text-xl font-semibold text-left w-full">Uploaded Files</h2>
            {uploadedFiles.map((file, index) => (
              // Use a unique key for list items, here index is okay for simplicity
              <FileCard
                key={index}
                title={file.title}
                mimeType={file.mimeType}
                size={file.size}
                extension={file.extension}
                onDownload={() => alert(`Downloading ${file.title}`)} // Placeholder for download logic
              />
            ))}
          </div>
        )}
      </section>
    </DefaultLayout>
  );
}