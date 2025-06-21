import { Card, CardBody } from "@heroui/card";
import type { FC } from "react";
import { FileIcon, defaultStyles } from "react-file-icon";
import { Download } from "lucide-react";
import { Button } from "@heroui/button";

type FileCardProps = {
    title: string;
    mimeType: string;
    storedAt: string;
    size: string;
    extension: keyof typeof defaultStyles;
    onDownload?: () => void;
};

const FileCard: FC<FileCardProps> = ({
    title,
    size,
    storedAt,
    extension,
    onDownload,
}) => {

    const formattedStoredAt = new Date(storedAt).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    });


    return (
        <Card className="max-w-xl w-full">
            <CardBody>
                <div className="flex items-center justify-between gap-4">
                    {/* Left side: Icon + details */}
                    <div className="flex items-center gap-4">
                        {/* Icon */}
                        <div className="flex items-center justify-center w-12 h-12">
                            <FileIcon extension={extension} {...defaultStyles[extension] || {}} />
                        </div>

                        {/* File Details */}
                        <div className="flex flex-col justify-center text-left">
                            <h2 className="text-base font-semibold">{title}</h2>
                            <p className="text-sm text-gray-500">{formattedStoredAt}</p>
                            <p className="text-sm text-gray-400">{size}</p>
                        </div>
                    </div>

                    {/* Right side: Download Icon */}
                    <Button
                        onPress={onDownload}
                        className="text-gray-400 hover:text-white transition-colors"
                        aria-label="Download file"
                    >
                        <Download size={20} />
                    </Button>
                </div>
            </CardBody>
        </Card>
    );
};

export default FileCard;
