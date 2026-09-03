import { useCallback, useRef } from 'react'
import { Upload } from 'lucide-react'
import { cn } from '../lib/utils'

const ACCEPT = '.pdf,.docx,.txt,.md'

interface FileDropzoneProps {
  content: string
  onContentChange: (value: string) => void
  file: File | null
  onFileChange: (file: File | null) => void
}

export function FileDropzone({ content, onContentChange, file, onFileChange }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const picked = files?.[0]
      if (!picked) return
      onFileChange(picked)
      onContentChange('')
    },
    [onContentChange, onFileChange],
  )

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div className="relative">
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        className={cn(
          'relative min-h-[280px] rounded-2xl border border-gray-200 bg-white',
          file && 'ring-2 ring-brand/20',
        )}
      >
        <textarea
          value={file ? `Attached: ${file.name}` : content}
          onChange={(e) => {
            onFileChange(null)
            onContentChange(e.target.value)
          }}
          readOnly={Boolean(file)}
          placeholder="Paste article, paper, book chapter or notes here — or upload a PDF / Word document with the button below."
          className="min-h-[280px] w-full resize-none rounded-2xl bg-transparent p-5 pr-16 text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none"
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="absolute bottom-4 right-4 flex h-11 w-11 items-center justify-center rounded-full bg-brand text-white shadow-md hover:bg-brand-dark"
          title="Upload file"
        >
          <Upload className="h-5 w-5" />
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      <p className="mt-3 text-xs text-gray-400">
        PDF (up to 500 pages), Word (.docx), TXT or Markdown — parsed on the server.
      </p>
    </div>
  )
}
