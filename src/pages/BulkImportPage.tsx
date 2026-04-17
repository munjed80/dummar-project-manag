import { useState } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Spinner, Warning, UploadSimple, FileCsv, Scan, CheckCircle, XCircle } from '@phosphor-icons/react';
import { toast } from 'sonner';

type Tab = 'csv' | 'scan';

interface PreviewRow {
  row_number: number;
  contract_number: string;
  title: string;
  contractor_name: string;
  is_valid: boolean;
  validation_errors: string[];
}

interface PreviewResult {
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  rows: PreviewRow[];
  warnings: string[];
}

interface ImportResult {
  total_processed: number;
  successful: number;
  failed: number;
  import_batch_id: string;
  documents: any[];
  errors: string[];
}

export default function BulkImportPage() {
  const [activeTab, setActiveTab] = useState<Tab>('csv');

  // CSV state
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [csvResult, setCsvResult] = useState<ImportResult | null>(null);

  // Scan state
  const [scanFiles, setScanFiles] = useState<File[]>([]);
  const [scanLoading, setScanLoading] = useState(false);
  const [scanResult, setScanResult] = useState<ImportResult | null>(null);

  const [error, setError] = useState('');

  const handleCsvFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setCsvFile(file);
    setPreview(null);
    setCsvResult(null);
    setError('');
  };

  const handlePreview = async () => {
    if (!csvFile) return;
    setPreviewLoading(true);
    setError('');
    try {
      const data = await apiService.previewCsvImport(csvFile);
      setPreview(data);
      if (data.warnings?.length) {
        data.warnings.forEach((w: string) => toast.warning(w));
      }
    } catch {
      setError('فشل معاينة الملف. تأكد من صحة التنسيق.');
      toast.error('فشل معاينة الملف');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleExecuteImport = async () => {
    if (!csvFile) return;
    setImportLoading(true);
    setError('');
    try {
      const data = await apiService.executeCsvImport(csvFile);
      setCsvResult(data);
      toast.success(`تم استيراد ${data.successful} من ${data.total_processed} سجل بنجاح`);
    } catch {
      setError('فشل تنفيذ الاستيراد. حاول مرة أخرى.');
      toast.error('فشل تنفيذ الاستيراد');
    } finally {
      setImportLoading(false);
    }
  };

  const handleScanFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    setScanFiles(files);
    setScanResult(null);
    setError('');
  };

  const handleScanImport = async () => {
    if (scanFiles.length === 0) return;
    setScanLoading(true);
    setError('');
    try {
      const data = await apiService.bulkScanImport(scanFiles);
      setScanResult(data);
      toast.success(`تمت معالجة ${data.successful} من ${data.total_processed} ملف بنجاح`);
    } catch {
      setError('فشل معالجة الملفات الممسوحة. حاول مرة أخرى.');
      toast.error('فشل معالجة الملفات');
    } finally {
      setScanLoading(false);
    }
  };

  const renderImportResult = (result: ImportResult) => (
    <Card className="border-green-200 bg-green-50/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <CheckCircle size={22} className="text-green-600" />
          نتائج الاستيراد
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          <div className="text-center">
            <p className="text-2xl font-bold">{result.total_processed}</p>
            <p className="text-sm text-muted-foreground">إجمالي</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">{result.successful}</p>
            <p className="text-sm text-muted-foreground">ناجح</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-red-600">{result.failed}</p>
            <p className="text-sm text-muted-foreground">فاشل</p>
          </div>
          <div className="text-center">
            <p className="text-sm font-mono text-muted-foreground mt-1">{result.import_batch_id}</p>
            <p className="text-sm text-muted-foreground">رقم الدفعة</p>
          </div>
        </div>
        {result.errors?.length > 0 && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm font-semibold text-red-700 mb-1">أخطاء:</p>
            <ul className="text-sm text-red-600 list-disc list-inside space-y-1">
              {result.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <Layout>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">الاستيراد المجمّع</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Tab buttons */}
          <div className="flex gap-2 border-b pb-3">
            <Button
              variant={activeTab === 'csv' ? 'default' : 'outline'}
              onClick={() => setActiveTab('csv')}
              className="flex items-center gap-2"
            >
              <FileCsv size={20} />
              استيراد CSV/Excel
            </Button>
            <Button
              variant={activeTab === 'scan' ? 'default' : 'outline'}
              onClick={() => setActiveTab('scan')}
              className="flex items-center gap-2"
            >
              <Scan size={20} />
              استيراد ملفات ممسوحة
            </Button>
          </div>

          {error && (
            <div className="text-center py-4 text-destructive flex flex-col items-center gap-2">
              <Warning size={28} />
              <p>{error}</p>
            </div>
          )}

          {/* CSV/Excel Import Tab */}
          {activeTab === 'csv' && (
            <div className="space-y-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col sm:flex-row items-start sm:items-end gap-3">
                    <div className="flex-1 w-full">
                      <label className="block text-sm font-medium mb-1">اختر ملف CSV أو Excel</label>
                      <input
                        type="file"
                        accept=".csv,.xlsx,.xls"
                        onChange={handleCsvFileChange}
                        className="block w-full text-sm border rounded-md p-2 file:ml-3 file:px-3 file:py-1 file:rounded file:border-0 file:bg-primary file:text-primary-foreground file:cursor-pointer"
                      />
                    </div>
                    <Button
                      onClick={handlePreview}
                      disabled={!csvFile || previewLoading}
                      className="flex items-center gap-2"
                    >
                      {previewLoading ? <Spinner className="animate-spin" size={18} /> : <UploadSimple size={18} />}
                      معاينة
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Preview results */}
              {preview && (
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <CardTitle className="text-lg">معاينة البيانات</CardTitle>
                      <div className="flex gap-2">
                        <Badge className="bg-blue-100 text-blue-800">الإجمالي: {preview.total_rows}</Badge>
                        <Badge className="bg-green-100 text-green-800">صالح: {preview.valid_rows}</Badge>
                        {preview.invalid_rows > 0 && (
                          <Badge className="bg-red-100 text-red-800">غير صالح: {preview.invalid_rows}</Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-right">الصف</TableHead>
                            <TableHead className="text-right">رقم العقد</TableHead>
                            <TableHead className="text-right">العنوان</TableHead>
                            <TableHead className="text-right">المقاول</TableHead>
                            <TableHead className="text-right">الحالة</TableHead>
                            <TableHead className="text-right">الأخطاء</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {preview.rows.length === 0 ? (
                            <TableRow>
                              <TableCell colSpan={6} className="text-center py-6 text-muted-foreground">
                                لا توجد بيانات
                              </TableCell>
                            </TableRow>
                          ) : (
                            preview.rows.map((row) => (
                              <TableRow key={row.row_number} className={!row.is_valid ? 'bg-red-50' : ''}>
                                <TableCell className="font-mono">{row.row_number}</TableCell>
                                <TableCell>{row.contract_number || '-'}</TableCell>
                                <TableCell>{row.title || '-'}</TableCell>
                                <TableCell>{row.contractor_name || '-'}</TableCell>
                                <TableCell>
                                  {row.is_valid ? (
                                    <CheckCircle size={20} className="text-green-600" />
                                  ) : (
                                    <XCircle size={20} className="text-red-600" />
                                  )}
                                </TableCell>
                                <TableCell>
                                  {row.validation_errors?.length > 0 ? (
                                    <ul className="text-xs text-red-600 list-disc list-inside">
                                      {row.validation_errors.map((err, i) => (
                                        <li key={i}>{err}</li>
                                      ))}
                                    </ul>
                                  ) : (
                                    '-'
                                  )}
                                </TableCell>
                              </TableRow>
                            ))
                          )}
                        </TableBody>
                      </Table>
                    </div>

                    <div className="flex justify-end">
                      <Button
                        onClick={handleExecuteImport}
                        disabled={importLoading || preview.valid_rows === 0}
                        className="flex items-center gap-2"
                      >
                        {importLoading ? <Spinner className="animate-spin" size={18} /> : <UploadSimple size={18} />}
                        تنفيذ الاستيراد ({preview.valid_rows} سجل)
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {csvResult && renderImportResult(csvResult)}
            </div>
          )}

          {/* Scanned Files Import Tab */}
          {activeTab === 'scan' && (
            <div className="space-y-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col sm:flex-row items-start sm:items-end gap-3">
                    <div className="flex-1 w-full">
                      <label className="block text-sm font-medium mb-1">اختر ملفات PDF أو صور</label>
                      <input
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                        multiple
                        onChange={handleScanFilesChange}
                        className="block w-full text-sm border rounded-md p-2 file:ml-3 file:px-3 file:py-1 file:rounded file:border-0 file:bg-primary file:text-primary-foreground file:cursor-pointer"
                      />
                    </div>
                    <Button
                      onClick={handleScanImport}
                      disabled={scanFiles.length === 0 || scanLoading}
                      className="flex items-center gap-2"
                    >
                      {scanLoading ? <Spinner className="animate-spin" size={18} /> : <Scan size={18} />}
                      بدء المعالجة
                    </Button>
                  </div>
                  {scanFiles.length > 0 && (
                    <p className="text-sm text-muted-foreground mt-2">
                      تم اختيار {scanFiles.length} ملف
                    </p>
                  )}
                </CardContent>
              </Card>

              {scanResult && renderImportResult(scanResult)}
            </div>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
