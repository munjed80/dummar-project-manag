import { useEffect, useState } from 'react';
import { DownloadSimple, X, DeviceMobile } from '@phosphor-icons/react';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const DISMISS_KEY = 'citizen_install_banner_dismissed_v1';

function detectIos(): boolean {
  if (typeof window === 'undefined') return false;
  const ua = window.navigator.userAgent;
  return (
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === 'MacIntel' &&
      ((navigator as { maxTouchPoints?: number }).maxTouchPoints ?? 0) > 1)
  );
}

function isStandalone(): boolean {
  if (typeof window === 'undefined') return false;
  if (window.matchMedia?.('(display-mode: standalone)').matches) return true;
  return Boolean((window.navigator as { standalone?: boolean }).standalone);
}

/**
 * Small, polished install banner shown only on the citizen portal
 * (public landing, complaint submit, complaint track, citizen dashboard).
 *
 * Visual identity: navy/blue (matches the app primary), NOT a yellow warning.
 * Dismissible — preference is persisted in localStorage. Mobile / QR friendly.
 *
 * Behaviour:
 *   - If `beforeinstallprompt` was captured → shows "تثبيت التطبيق" button
 *     and triggers the native prompt.
 *   - If on iPhone/iPad (no native prompt) → shows Safari "Add to Home
 *     Screen" instructions inline.
 *   - Otherwise → shows generic Android/Chrome instructions.
 *   - If app is already installed (standalone) → renders nothing.
 */
export function CitizenInstallBanner() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState<boolean>(() => isStandalone());
  const [dismissed, setDismissed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === '1';
    } catch {
      return false;
    }
  });
  const [showHelp, setShowHelp] = useState(false);

  const ios = detectIos();

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setDeferredPrompt(null);
    };
    window.addEventListener('beforeinstallprompt', handler);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', handler);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  if (installed || dismissed) return null;

  const handleDismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, '1');
    } catch {
      /* ignore quota / private mode */
    }
    setDismissed(true);
  };

  const handleInstall = async () => {
    if (deferredPrompt) {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        setDeferredPrompt(null);
        setInstalled(true);
      }
      return;
    }
    // No native prompt — toggle inline help with platform-specific Arabic text.
    setShowHelp((v) => !v);
  };

  const buttonLabel = deferredPrompt ? 'تثبيت التطبيق' : 'إضافة إلى الشاشة الرئيسية';

  return (
    <div className="container mx-auto px-4 pt-4" dir="rtl">
      <div className="rounded-xl border border-[#123B63]/20 bg-gradient-to-l from-[#123B63] to-[#1d568f] text-white shadow-sm overflow-hidden">
        <div className="flex items-start gap-3 px-4 py-3 md:px-5 md:py-4">
          <div className="hidden sm:flex shrink-0 w-10 h-10 rounded-lg bg-white/10 items-center justify-center">
            <DeviceMobile size={22} weight="duotone" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm md:text-base leading-6">
              حمّل تطبيق شكاوى المواطنين على هاتفك لتقديم ومتابعة الشكاوى بسهولة.
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleInstall}
                className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs md:text-sm font-bold text-[#123B63] hover:bg-white/90 transition-colors"
              >
                <DownloadSimple size={16} weight="bold" />
                {buttonLabel}
              </button>
              {!deferredPrompt && (
                <span className="text-[11px] md:text-xs text-white/80">
                  {ios
                    ? 'متاح على iPhone و iPad عبر Safari'
                    : 'متاح على Android عبر Chrome'}
                </span>
              )}
            </div>

            {showHelp && !deferredPrompt && (
              <div className="mt-3 rounded-lg bg-white/10 px-3 py-2 text-xs md:text-sm leading-6">
                {ios ? (
                  <p>
                    لتثبيت التطبيق على iPhone: افتح الموقع من Safari، اضغط زر المشاركة،
                    ثم اختر <span className="font-semibold">إضافة إلى الشاشة الرئيسية</span>.
                  </p>
                ) : (
                  <p>
                    لتثبيت التطبيق على Android: افتح الموقع من Chrome، اضغط القائمة ⋮،
                    ثم اختر <span className="font-semibold">إضافة إلى الشاشة الرئيسية</span> أو
                    <span className="font-semibold"> تثبيت التطبيق</span>.
                  </p>
                )}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={handleDismiss}
            aria-label="إغلاق"
            title="إغلاق"
            className="shrink-0 -mt-1 -ml-1 rounded-md p-1 text-white/70 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={16} weight="bold" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default CitizenInstallBanner;
