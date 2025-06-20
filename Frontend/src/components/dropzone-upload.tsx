import React, { useState, useRef } from "react";
import axios from "axios";
import { FileIcon, defaultStyles } from "react-file-icon";
import { Card, CardBody } from "@heroui/card";
import { Progress } from "@heroui/progress";

type DropzoneUploadProps = {
    onFileUpload: (fileData: {
        title: string;
        mimeType: string;
        size: string;
        extension: keyof typeof defaultStyles;
    }) => void;
};

type UploadingFile = {
    file: File;
    progress: number;
};

const DropzoneUpload: React.FC<DropzoneUploadProps> = ({ onFileUpload }) => {
    const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleFiles = (selectedFiles: FileList | null) => {
        if (!selectedFiles) return;
        const filesArray = Array.from(selectedFiles);

        for (const file of filesArray) {
            const newUpload: UploadingFile = { file, progress: 0 };
            setUploadingFiles((prev) => [...prev, newUpload]);

            const formData = new FormData();
            formData.append("uploaded_files", file); // ✅ Make sure this matches backend

            console.log("Uploading:", file.name, formData.get("uploaded_files"));

            axios
                .post("http://localhost:8888/upload", formData, {
                    onUploadProgress: (progressEvent) => {
                        const progress = Math.round(
                            (progressEvent.loaded * 100) / (progressEvent.total || 1)
                        );
                        setUploadingFiles((prev) =>
                            prev.map((f) =>
                                f.file === file ? { ...f, progress } : f
                            )
                        );
                    },
                })
                .then(() => {
                    console.log(`${file.name} uploaded`);
                    const extension = file.name.split(".").pop()?.toLowerCase() || "txt";

                    onFileUpload({
                        title: file.name,
                        mimeType: file.type,
                        size: `${(file.size / 1024 / 1024).toFixed(2)} MB`,
                        extension: extension as keyof typeof defaultStyles,
                    });

                    setUploadingFiles((prev) =>
                        prev.filter((f) => f.file !== file)
                    );
                })
                .catch((err) => {
                    console.error(`Error uploading ${file.name}`, err);
                    setUploadingFiles((prev) =>
                        prev.filter((f) => f.file !== file)
                    );
                });
        }
    };

    return (
        <div
            className="w-full max-w-xl p-4 border-2 border-dashed rounded-lg text-white bg-zinc-900 cursor-pointer"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
                e.preventDefault();
                handleFiles(e.dataTransfer.files);
            }}
            onClick={() => inputRef.current?.click()}
        >
            <p className="text-center text-gray-400">Click or drop files here</p>
            <input
                type="file"
                ref={inputRef}
                multiple
                className="hidden"
                onChange={(e) => handleFiles(e.target.files)}
            />

            <div className="mt-4 space-y-3">
                {uploadingFiles.map(({ file, progress }, idx) => {
                    const ext = file.name.split(".").pop()?.toLowerCase() || "txt";
                    return (
                        <Card key={idx} className="bg-zinc-800">
                            <CardBody>
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10">
                                        <FileIcon extension={ext} {...(defaultStyles[ext as keyof typeof defaultStyles] || {})} />
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm font-medium">{file.name}</p>
                                        <p className="text-xs text-gray-400">
                                            {(file.size / 1024 / 1024).toFixed(2)} MB
                                        </p>
                                        <Progress value={progress} className="mt-1" />
                                    </div>
                                </div>
                            </CardBody>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
};

export default DropzoneUpload;
