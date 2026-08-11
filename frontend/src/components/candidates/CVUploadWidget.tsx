import { useState, useRef } from 'react';
import Button from '../shared/Button';
import ErrorMessage from '../shared/ErrorMessage';
import { uploadCandidateCV } from '../../api/candidates';
import type { CVUploadResponse } from '../../types';

const ACCEPTED_TYPES = ['.pdf', '.docx'];
const ACCEPTED_MIME = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

interface CVUploadWidgetProps {
  candidateId: number;
  onSuccess: (response: CVUploadResponse) => void;
}

function validateFile(file: File): string | null {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  if (!ACCEPTED_TYPES.includes(ext) || !ACCEPTED_MIME.includes(file.type)) {
    return 'Only PDF and DOCX files are accepted. Please choose a valid file.';
  }
  return null;
}

export default function CVUploadWidget({ candidateId, onSuccess }: CVUploadWidgetProps) {
  const [dragging, setDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    const err = validateFile(file);
    if (err) {
      setFileError(err);
      setSelectedFile(null);
    } else {
      setFileError(null);
      setSelectedFile(file);
      setUploadError(null);
    }
  };

  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(true);
  };

  const onDragLeave = () => setDragging(false);

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setUploadError(null);
    try {
      const result = await uploadCandidateCV(candidateId, selectedFile);
      onSuccess(result);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  if (uploading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-14 px-6 bg-white rounded-xl border border-slate-100 shadow-card">
        <div className="relative">
          <div className="w-14 h-14 rounded-full border-4 border-slate-100 border-t-primary-start animate-spin" />
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-primary-dark">Parsing CV…</p>
          <p className="text-xs text-slate-400 mt-1">
            Extracting skills, experience, and education. This may take a few seconds.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-card p-6">
      <h3 className="text-sm font-semibold text-primary-dark mb-4">Upload CV</h3>

      {/* Drop zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
        aria-label="Upload CV file — click or drag and drop"
        className={[
          'flex flex-col items-center justify-center gap-3 p-10 rounded-lg border-2 border-dashed cursor-pointer transition-all duration-150',
          dragging
            ? 'border-primary-start bg-primary-start/5'
            : 'border-slate-200 hover:border-primary-start/50 hover:bg-slate-50',
        ].join(' ')}
      >
        <svg className="w-10 h-10 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <div className="text-center">
          <p className="text-sm font-medium text-primary-dark">
            Drop your file here, or <span className="text-primary-start">browse</span>
          </p>
          <p className="text-xs text-slate-400 mt-1">PDF or DOCX · Max recommended 10 MB</p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx"
          className="sr-only"
          onChange={onInputChange}
          aria-label="CV file input"
        />
      </div>

      {/* File type error */}
      {fileError && (
        <div className="mt-3">
          <ErrorMessage message={fileError} />
        </div>
      )}

      {/* Selected file preview */}
      {selectedFile && !fileError && (
        <div className="mt-3 flex items-center gap-3 px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg">
          <svg className="w-4 h-4 text-primary-start shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="text-xs font-medium text-primary-dark flex-1 truncate">{selectedFile.name}</span>
          <button
            onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
            className="text-slate-400 hover:text-slate-600 transition-colors"
            aria-label="Remove selected file"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Upload error */}
      {uploadError && (
        <div className="mt-3">
          <ErrorMessage message={uploadError} />
        </div>
      )}

      {/* Upload button */}
      <div className="mt-4 flex justify-end">
        <Button onClick={handleUpload} disabled={!selectedFile || Boolean(fileError)} loading={uploading}>
          Parse CV
        </Button>
      </div>
    </div>
  );
}
