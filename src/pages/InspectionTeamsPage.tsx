import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function InspectionTeamsPage() {
  return (
    <Layout>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">فرق التفتيش</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-muted-foreground">
          <p>هذه وحدة مستقلة لجدولة ومتابعة جولات التفتيش، وليست الفرق التنفيذية.</p>
          <p>تدعم متابعة مسارات الزيارات، توزيع الجولات، وتوثيق نتائج التفتيش ميدانياً.</p>
        </CardContent>
      </Card>
    </Layout>
  );
}
