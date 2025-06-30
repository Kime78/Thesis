import { Card, CardBody } from "@heroui/card";
import type { FC } from "react";
import { FileIcon, defaultStyles } from "react-file-icon";
import {  Download, Trash } from "lucide-react";
import { Button } from "@heroui/button";

type FileCardProps = {
    title: string;
    mimeType: string;
    storedAt: string;
    size: string;
    extension: keyof typeof defaultStyles;
    onDownload?: () => void;
    onDelete?: () => void;
    uploading: boolean;
};

const FileCard: FC<FileCardProps> = ({
    title,
    size,
    storedAt,
    extension,
    onDownload,
    onDelete,
    uploading
}) => {

    const formattedStoredAt = new Date(storedAt).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    });


    return (
        <Card className="max-w-xl w-full">
            <CardBody>
                <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-4 overflow-hidden"> {/* Add overflow-hidden to the parent */}
                        <div className="flex-shrink-0 w-12 h-12"> {/* Prevent the icon from shrinking */}
                            <FileIcon extension={extension} {...defaultStyles[extension] || {}} />
                        </div>
                        <div className="flex flex-col justify-center text-left min-w-0"> {/* Add min-w-0 for flex context */}
                            {/* Apply the truncate class here */}
                            <h2 className="text-base font-semibold truncate">{title}</h2>
                            <p className="text-sm text-gray-500">{formattedStoredAt}</p>
                            <p className="text-sm text-gray-400">{size}</p>
                        </div>
                    </div>
                    
                    {!uploading && (
                        <div className="flex flex-shrink-0 items-center gap-2"> {/* Prevent buttons from shrinking */}
                            <Button
                                onPress={onDelete}
                                className="text-red-400 hover:text-white transition-colors"
                                aria-label="Delete file"
                            >
                                <Trash size={20}></Trash>
                            </Button>
                            <Button
                                onPress={onDownload}
                                className="text-gray-400 hover:text-white transition-colors"
                                aria-label="Download file"
                            >
                                <Download size={20} />
                            </Button>
                        </div>
                    )}
                </div>
            </CardBody>
        </Card>
    );
};

export default FileCard;
