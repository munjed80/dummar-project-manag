import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { apiService } from '@/services/api';
import { Upload, X, FileText, Image, Spinner } from '@phosphor-icons/react';
import { toast } from 'sonner';

const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif'];
const ALLOWED_DOC_TYPES = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

const API_BASE_URL = 'http://localhost:8000';

interface FileUploadProps {
  category: string;
  accept?: 'images' | 'documents' | 'all';
  multiple?: boolean;
  existingFiles?: string[];
  onUploadComplete?: (files: string[]) => void;
  label?: string;
}

export function FileUpload({ category, accept = 'all', multiple = true, existingFiles = [], onUploadComplete, label }: FileUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<{ path: string; original_name: string }[]>(
    existingFiles.map(f => ({ path: f, original_name: f.split('/').pop() || f }))
  );
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const allowedTypes = accept === 'images' ? ALLOWED_IMAGE_TYPES
    : accept === 'documents' ? ALLOWED_DOC_TYPES
    : [...ALLOWED_IMAGE_TYPES, ...ALLOWED_DOC_TYPES];

  const acceptStr = accept === 'images' ? '.jpg,.jpeg,.png,.gif'
    : accept === 'documents' ? '.pdf,.doc,.docx'
    : '.jpg,.jpeg,.png,.gif,.pdf,.doc,.docx';

  const validateFile = (file: File): string | null => {
    if (!allowedTypes.includes(file.type)) {
      return `نوع الملف غير مسموح: ${file.name}`;
    }
    if (file.size > MAX_SIZE) {
      return `حجم الملف كبير جداً (الحد الأقصى 10 ميغابايت): ${file.name}`;
    }
    return null;
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const fileArray = Array.from(files);
    for (const file of fileArray) {
      const error = validateFile(file);
      if (error) {
        toast.error(error);
        return;
      }
    }

    setUploading(true);
    const newFiles: { path: string; original_name: string }[] = [];

    for (const file of fileArray) {
      try {
        const result = await apiService.uploadFile(file, category);
        newFiles.push({ path: result.path, original_name: result.original_name });
      } catch {
        toast.error(`فشل رفع الملف: ${file.name}`);
      }
    }

    if (newFiles.length > 0) {
      const allFiles = [...uploadedFiles, ...newFiles];
      setUploadedFiles(allFiles);
      toast.success(`تم رفع ${newFiles.length} ملف بنجاح`);
      onUploadComplete?.(allFiles.map(f => f.path));
    }

    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeFile = (index: number) => {
    const newFiles = uploadedFiles.filter((_, i) => i !== index);
    setUploadedFiles(newFiles);
    onUploadComplete?.(newFiles.map(f => f.path));
  };

  const isImage = (path: string) => {
    return /\.(jpg|jpeg|png|gif)$/i.test(path);
  };

  return (
    <div className="space-y-3">
      {label && <label className="text-sm font-medium">{label}</label>}

      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? <Spinner className="animate-spin ml-2" size={16} /> : <Upload className="ml-2" size={16} />}
          {uploading ? 'جاري الرفع...' : 'رفع ملف'}
        </Button>
        <span className="text-xs text-muted-foreground">
          الحد الأقصى: 10 ميغابايت | {accept === 'images' ? 'صور فقط' : accept === 'documents' ? 'مستندات فقط' : 'صور ومستندات'}
        </span>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept={acceptStr}
        multiple={multiple}
        onChange={handleFileSelect}
        className="hidden"
      />

      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          {uploadedFiles.map((file, idx) => (
            <div key={idx} className="flex items-center gap-2 p-2 bg-muted rounded-md">
              {isImage(file.path) ? <Image size={18} className="text-blue-600" /> : <FileText size={18} className="text-orange-600" />}
              <a
                href={`${API_BASE_URL}${file.path}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline flex-1 truncate"
              >
                {file.original_name}
              </a>
              <Button type="button" variant="ghost" size="sm" onClick={() => removeFile(idx)} className="h-6 w-6 p-0">
                <X size={14} />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
