import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { DownloadSimple, X } from '@phosphor-icons/react';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

/**
 * PWA Install Prompt — shows a dismissible banner when the browser
 * detects the app can be installed. Arabic UI with RTL layout.
 */
export function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Check if user previously dismissed
    if (localStorage.getItem('pwa-install-dismissed') === '1') {
      setDismissed(true);
      return;
    }

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      setDeferredPrompt(null);
    }
  };

  const handleDismiss = () => {
    setDismissed(true);
    setDeferredPrompt(null);
    localStorage.setItem('pwa-install-dismissed', '1');
  };

  if (!deferredPrompt || dismissed) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:max-w-sm z-50 bg-primary text-primary-foreground rounded-lg shadow-lg p-4 flex items-center gap-3">
      <DownloadSimple size={28} className="shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold">تثبيت التطبيق</p>
        <p className="text-xs opacity-90">ثبّت المنصة على جهازك للوصول السريع</p>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <Button
          size="sm"
          variant="secondary"
          onClick={handleInstall}
          className="text-xs px-3"
        >
          تثبيت
        </Button>
        <button
          onClick={handleDismiss}
          className="p-1 rounded hover:bg-primary/80 transition-colors"
          aria-label="إغلاق"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}
