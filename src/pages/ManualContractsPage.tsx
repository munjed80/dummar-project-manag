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
            <h1 className="text-2xl md:text-3xl font-bold">العقود التشغيلية</h1>
            <p className="text-muted-foreground mt-1">
              إدارة العقود غير الاستثمارية فقط (عقود صيانة، خدمات، تنفيذ، متعهدين، ومشاريع تشغيلية).
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Link to="/investment-contracts">
              <Button variant="outline" className="gap-2">
                عرض العقود الاستثمارية
              </Button>
            </Link>
            <Link to="/contract-intelligence">
              <Button variant="outline" className="gap-2">
                <Brain size={18} />
                مركز ذكاء العقود
              </Button>
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText size={22} />
                العقود التشغيلية (إدارة يدوية)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                هذه الصفحة مخصصة للعقود التشغيلية والإدارية فقط وليست للعقود الاستثمارية.
              </p>
              <Link to="/contracts">
                <Button className="w-full gap-2">
                  فتح العقود التشغيلية
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
