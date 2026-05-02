import { useState } from 'react';
import { Robot } from '@phosphor-icons/react';
import { SmartAssistantDrawer } from '@/components/SmartAssistantDrawer';

/**
 * Topbar icon that opens the Decision Center smart-assistant drawer.
 * Lives next to the notification bell — intentionally NOT a sidebar entry.
 */
export function SmartAssistantButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title="مركز القرار الذكي"
        aria-label="مركز القرار الذكي"
        className="relative inline-flex items-center justify-center rounded-lg border border-transparent p-2 text-primary-foreground transition-colors hover:bg-primary-foreground/10 hover:border-primary-foreground/25"
      >
        <Robot size={22} />
      </button>
      <SmartAssistantDrawer open={open} onOpenChange={setOpen} />
    </>
  );
}

export default SmartAssistantButton;
