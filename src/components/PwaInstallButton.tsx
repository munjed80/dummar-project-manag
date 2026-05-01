import { useEffect, useRef, useState } from 'react';
import { DownloadSimple, DeviceMobile, CheckCircle, Info } from '@phosphor-icons/react';
import { cn } from '@/lib/utils';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

type Platform = 'installable' | 'installed' | 'ios' | 'unsupported';

function detectIos(): boolean {
  if (typeof window === 'undefined') return false;
  const ua = window.navigator.userAgent;
  const isIos = /iPad|iPhone|iPod/.test(ua) ||
    // iPadOS 13+ reports as Mac with touch
    (navigator.platform === 'MacIntel' && ((navigator as { maxTouchPoints?: number }).maxTouchPoints ?? 0) > 1);
  return isIos;
}

function isStandalone(): boolean {
  if (typeof window === 'undefined') return false;
  if (window.matchMedia?.('(display-mode: standalone)').matches) return true;
  // iOS Safari standalone flag
  return Boolean((window.navigator as { standalone?: boolean }).standalone);
}

/**
 * Compact PWA install control for the topbar.  Replaces the previous
 * floating banner.  Handles four cases:
 *   - installable      → fires the native `beforeinstallprompt`
 *   - installed        → shows "التطبيق مثبت" and hides itself
 *   - ios              → shows Arabic Safari instructions in a popover
 *   - unsupported      → shows a graceful Arabic help message
 */
export function PwaInstallButton() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState<boolean>(() => isStandalone());
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const ios = detectIos();

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener('beforeinstallprompt', handler);

    const onInstalled = () => {
      setInstalled(true);
      setDeferredPrompt(null);
    };
    window.addEventListener('appinstalled', onInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handler);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  if (installed) {
    return (
      <div
        className="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-primary-foreground/25 bg-primary-foreground/10 px-2.5 py-1.5 text-[11px] text-primary-foreground"
        title="التطبيق مثبت على جهازك"
      >
        <CheckCircle size={14} weight="fill" className="text-emerald-300" />
        <span>التطبيق مثبت</span>
      </div>
    );
  }

  const platform: Platform = deferredPrompt ? 'installable' : (ios ? 'ios' : 'unsupported');

  const handleInstall = async () => {
    if (platform === 'installable' && deferredPrompt) {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        setDeferredPrompt(null);
        setInstalled(true);
      }
      return;
    }
    // For ios / unsupported, open the help popover
    setOpen((v) => !v);
  };

  const Icon = platform === 'ios' ? DeviceMobile
             : platform === 'unsupported' ? Info
             : DownloadSimple;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={handleInstall}
        className={cn(
          'relative inline-flex items-center justify-center rounded-lg border p-2 transition-colors',
          open
            ? 'bg-primary-foreground/20 text-primary-foreground border-primary-foreground/35'
            : 'text-primary-foreground hover:bg-primary-foreground/10 border-transparent hover:border-primary-foreground/25',
        )}
        title="تثبيت التطبيق"
        aria-label="تثبيت التطبيق"
      >
        <Icon size={20} />
      </button>

      {open && platform !== 'installable' && (
        <div
          className="absolute left-0 top-full mt-2 w-80 bg-white rounded-lg shadow-xl border z-50 overflow-hidden text-slate-800"
          dir="rtl"
        >
          <div className="px-4 py-3 border-b bg-slate-50">
            <h3 className="font-bold text-sm">تثبيت التطبيق</h3>
          </div>
          <div className="px-4 py-3 text-sm leading-6 space-y-2">
            {platform === 'ios' ? (
              <p>
                لتثبيت التطبيق على iPhone: افتح الموقع من Safari، اضغط زر المشاركة،
                ثم اختر <span className="font-semibold">Add to Home Screen</span>.
              </p>
            ) : (
              <>
                <p>متصفحك لا يدعم التثبيت التلقائي للتطبيق.</p>
                <p className="text-slate-500 text-xs">
                  جرّب فتح الموقع من متصفح Chrome أو Edge على الكمبيوتر، أو من Safari على iPhone،
                  ثم استخدم خيار "تثبيت التطبيق" أو "إضافة إلى الشاشة الرئيسية".
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default PwaInstallButton;
