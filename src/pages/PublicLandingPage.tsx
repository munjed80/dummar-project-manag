import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PublicShell } from '@/components/PublicHeader';
import { Plus, MagnifyingGlass, ChatCircleDots, Clock, CheckCircle, ArrowLeft } from '@phosphor-icons/react';

/**
 * Public landing page shown to unauthenticated visitors at `/`.
 * The product's primary user action — submitting a complaint — must be
 * the very first thing visible. Citizens should never have to find a
 * staff login to start.
 */
export default function PublicLandingPage() {
  return (
    <PublicShell>
      <div className="container mx-auto px-4 py-8 md:py-14 max-w-5xl">
        {/* Hero */}
        <div className="text-center mb-8 md:mb-12">
          <h2 className="text-2xl md:text-4xl font-bold text-foreground">
            منصة استقبال الطلبات والشكاوى — إدارة التجمع - مشروع دمر
          </h2>
          <p className="mt-3 text-sm md:text-base text-muted-foreground max-w-2xl mx-auto">
            قدّم طلبك أو شكواك مباشرة، وتابع حالتها برقم المتابعة في أي وقت. سيصل
            طلبك للجهة المعنية وستتم معالجته ضمن خطة العمل اليومية للمشروع.
          </p>
        </div>

        {/* Two main CTAs */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
          <Card className="border-2 border-primary/30 hover:border-primary transition-colors">
            <CardContent className="pt-8 pb-8 px-6 text-center space-y-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                <Plus size={32} className="text-primary" weight="bold" />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-1">تقديم طلب / شكوى جديدة</h3>
                <p className="text-sm text-muted-foreground">
                  املأ نموذجاً قصيراً يصف الطلب أو المشكلة والعنوان التفصيلي، وستحصل على رقم متابعة فوري.
                </p>
              </div>
              <Link to="/complaints/new" className="block">
                <Button size="lg" className="w-full gap-2">
                  ابدأ بتقديم الطلب / الشكوى
                  <ArrowLeft size={18} />
                </Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="border-2 border-accent/30 hover:border-accent transition-colors">
            <CardContent className="pt-8 pb-8 px-6 text-center space-y-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center">
                <MagnifyingGlass size={32} className="text-accent" weight="bold" />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-1">تتبع طلب / شكوى سابقة</h3>
                <p className="text-sm text-muted-foreground">
                  أدخل رقم المتابعة ورقم الهاتف لمعرفة حالة طلبك ومراحل تنفيذه.
                </p>
              </div>
              <Link to="/complaints/track" className="block">
                <Button size="lg" variant="secondary" className="w-full gap-2">
                  تتبع الطلب / الشكوى الآن
                  <ArrowLeft size={18} />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {/* Lifecycle explanation — what happens next */}
        <div className="mt-12 md:mt-16">
          <h3 className="text-center text-lg md:text-xl font-bold mb-6">كيف تُعالَج شكواك</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6 text-center space-y-2">
                <div className="mx-auto w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                  <ChatCircleDots size={22} className="text-blue-600" />
                </div>
                <h4 className="font-bold">١. الاستقبال</h4>
                <p className="text-sm text-muted-foreground">
                  تُسجَّل الشكوى وتحصل على رقم متابعة فوراً.
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6 text-center space-y-2">
                <div className="mx-auto w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center">
                  <Clock size={22} className="text-amber-600" />
                </div>
                <h4 className="font-bold">٢. الإحالة والتنفيذ</h4>
                <p className="text-sm text-muted-foreground">
                  تتم مراجعتها وتحويلها إلى مهمة تنفيذية للفريق المختص.
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6 text-center space-y-2">
                <div className="mx-auto w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckCircle size={22} className="text-green-600" />
                </div>
                <h4 className="font-bold">٣. الإغلاق والمتابعة</h4>
                <p className="text-sm text-muted-foreground">
                  تُحدَّث حالتها حتى الإغلاق ويمكنك تتبع كل المراحل.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Subtle staff entry note */}
        <p className="mt-10 md:mt-14 text-center text-xs text-muted-foreground">
          إذا كنت من فريق إدارة المشروع، يمكنك{' '}
          <Link to="/login" className="underline hover:text-foreground">
            تسجيل الدخول إلى لوحة التحكم
          </Link>
          .
        </p>
      </div>
    </PublicShell>
  );
}
