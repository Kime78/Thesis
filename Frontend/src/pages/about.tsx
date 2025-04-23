import DropzoneUpload from "@/components/dropzone-upload";
import FileCard from "@/components/file";
import { title } from "@/components/primitives";
import DefaultLayout from "@/layouts/default";
import { Button } from "@heroui/button";
import { Upload } from "lucide-react";
export default function DocsPage() {
  return (
    <DefaultLayout>
      <section className="flex flex-col items-center justify-center gap-4 py-8 md:py-10">
        <DropzoneUpload />
        <Button
          onPress={() => { }}
          className="text-gray-400 hover:text-white transition-colors"
          aria-label="Download file"
        >
          Upload
          <Upload size={20} />
        </Button>
        <FileCard
          title="Florin salam"
          mimeType="audio/mpeg"
          size="4.32 MB"
          extension="mp3"
        />
        <FileCard
          title="Virus"
          mimeType="application/xs-download"
          size="10.45 MB"
          extension="exe"
        />
        <FileCard
          title="Florin salam"
          mimeType="audio/mpeg"
          size="4.32 MB"
          extension="ai"
        />
        <FileCard
          title="Florin salam"
          mimeType="audio/mpeg"
          size="4.32 MB"
          extension="docx"
        />

      </section>
    </DefaultLayout>
  );
}
