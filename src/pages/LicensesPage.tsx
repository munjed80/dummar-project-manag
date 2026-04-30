import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function LicensesPage() {
  return (
    <Layout>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">التراخيص</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-muted-foreground">
          <p>هذه وحدة مستقلة للتراخيص الإدارية، وليست العقود التشغيلية.</p>
          <p>تهدف لإدارة طلبات الترخيص، المتطلبات النظامية، وإصدار الموافقات والتجديدات.</p>
        </CardContent>
      </Card>
    </Layout>
  );
}
