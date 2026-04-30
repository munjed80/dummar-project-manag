import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function ViolationsPage() {
  return (
    <Layout>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">المخالفات</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-muted-foreground">
          <p>هذه وحدة مستقلة لإدارة مخالفات البناء/الإشغال/النظافة/الأسواق، وليست الشكاوى.</p>
          <p>يمكن من خلال هذه الوحدة جدولة الفحص، توثيق المخالفة، وإدارة دورة الإجراء النظامي.</p>
        </CardContent>
      </Card>
    </Layout>
  );
}
