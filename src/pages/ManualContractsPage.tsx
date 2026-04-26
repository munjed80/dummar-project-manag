import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileText, Brain, ArrowLeft } from '@phosphor-icons/react';

export default function ManualContractsPage() {
  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold">صفحة العقود الأخرى للإدارة اليدوية</h1>
            <p className="text-muted-foreground mt-1">
              إدارة العقود اليدوية (العقود العامة + العقود الاستثمارية) مع إمكانية الانتقال إلى مركز ذكاء العقود.
            </p>
          </div>
          <Link to="/contract-intelligence">
            <Button variant="outline" className="gap-2">
              <Brain size={18} />
              الانتقال إلى مركز ذكاء العقود
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText size={22} />
                العقود (الإدارة اليدوية)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                إدخال ومتابعة العقود اليدوية المعتادة داخل النظام.
              </p>
              <Link to="/contracts">
                <Button className="w-full gap-2">
                  فتح صفحة العقود
                  <ArrowLeft size={16} />
                </Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText size={22} />
                العقود الاستثمارية
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                إدارة العقود الاستثمارية وملفاتها وبيانات المستثمرين يدوياً.
              </p>
              <Link to="/investment-contracts">
                <Button className="w-full gap-2">
                  فتح العقود الاستثمارية
                  <ArrowLeft size={16} />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
