import { config } from '@/config';

export type OfflineOperationType =
  | 'complaint_submit'
  | 'task_update'
  | 'repair_notes_add'
  | 'after_repair_photo_upload'
  | 'property_create_draft'
  | 'property_update_draft';

export type OfflineOperationStatus = 'pending' | 'syncing' | 'failed' | 'synced';

export interface OfflineAttachment {
  name: string;
  type: string;
  size: number;
  lastModified: number;
  blob: Blob;
}

export interface OfflineQueueItem {
  id?: number;
  operation_type: OfflineOperationType;
  endpoint: string;
  method: string;
  payload: any;
  attachments: OfflineAttachment[];
  created_at: string;
  retry_count: number;
  status: OfflineOperationStatus;
  idempotency_key: string;
  error_message?: string;
  last_attempt_at?: string;
}

export interface SyncState {
  isOnline: boolean;
  pendingCount: number;
  syncing: boolean;
  lastMessage: string | null;
}

const DB_NAME = 'dummar-offline-sync';
const DB_VERSION = 1;
const STORE_NAME = 'offline_queue';
const MAX_RETRIES = 8;
const TRANSIENT_HTTP_CODES = new Set([502, 503, 504]);
const API_BASE_URL = config.API_BASE_URL;

let dbPromise: Promise<IDBDatabase> | null = null;

function openDB(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      store.createIndex('status', 'status', { unique: false });
      store.createIndex('created_at', 'created_at', { unique: false });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbPromise;
}

function tx<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDB().then((db) => new Promise<T>((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, mode);
    const store = transaction.objectStore(STORE_NAME);
    const request = run(store);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  }));
}

async function getAllItems(): Promise<OfflineQueueItem[]> {
  return tx<OfflineQueueItem[]>('readonly', (store) => store.getAll());
}

async function putItem(item: OfflineQueueItem): Promise<number> {
  return tx<IDBValidKey>('readwrite', (store) => store.put(item)).then((id) => Number(id));
}

async function updateItem(item: OfflineQueueItem): Promise<void> {
  await tx('readwrite', (store) => store.put(item));
}

async function deleteItem(id: number): Promise<void> {
  await tx('readwrite', (store) => store.delete(id));
}

export function generateIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function toOfflineAttachment(file: File): OfflineAttachment {
  return {
    name: file.name,
    type: file.type,
    size: file.size,
    lastModified: file.lastModified,
    blob: file,
  };
}

function fromOfflineAttachment(att: OfflineAttachment): File {
  return new File([att.blob], att.name, {
    type: att.type,
    lastModified: att.lastModified,
  });
}

export function shouldQueueForOffline(error: unknown): boolean {
  if (!navigator.onLine) return true;
  if (error instanceof TypeError) return true;
  if (error instanceof Error) {
    const anyErr = error as any;
    if (typeof anyErr.status === 'number' && TRANSIENT_HTTP_CODES.has(anyErr.status)) return true;
    if (typeof anyErr.message === 'string' && /network|failed to fetch|offline/i.test(anyErr.message)) return true;
  }
  return false;
}

class OfflineSyncManager {
  private state: SyncState = {
    isOnline: navigator.onLine,
    pendingCount: 0,
    syncing: false,
    lastMessage: null,
  };

  private listeners = new Set<(state: SyncState) => void>();
  private initialized = false;

  subscribe(listener: (state: SyncState) => void): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  private setState(next: Partial<SyncState>): void {
    this.state = { ...this.state, ...next };
    for (const listener of this.listeners) listener(this.state);
  }

  async init(): Promise<void> {
    if (this.initialized) return;
    this.initialized = true;
    await this.refreshPendingCount();
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);
    if (navigator.onLine) {
      void this.syncNow();
    }
  }

  private handleOnline = (): void => {
    this.setState({ isOnline: true, lastMessage: 'تم استعادة الاتصال، جاري المزامنة...' });
    void this.syncNow();
  };

  private handleOffline = (): void => {
    this.setState({ isOnline: false, lastMessage: 'أنت تعمل بدون اتصال' });
  };

  async refreshPendingCount(): Promise<void> {
    const items = await getAllItems();
    const pendingCount = items.filter((i) => i.status === 'pending' || i.status === 'failed').length;
    this.setState({ pendingCount });
  }

  async queueOperation(input: {
    operation_type: OfflineOperationType;
    endpoint: string;
    method: string;
    payload: any;
    attachments?: File[];
    idempotency_key?: string;
  }): Promise<number> {
    const attachments = (input.attachments || []).map(toOfflineAttachment);
    const item: OfflineQueueItem = {
      operation_type: input.operation_type,
      endpoint: input.endpoint,
      method: input.method,
      payload: input.payload,
      attachments,
      created_at: new Date().toISOString(),
      retry_count: 0,
      status: 'pending',
      idempotency_key: input.idempotency_key || generateIdempotencyKey(input.operation_type),
    };
    const id = await putItem(item);
    await this.refreshPendingCount();
    this.setState({ lastMessage: 'تم حفظ الطلب محليًا وسيتم إرساله عند عودة الاتصال' });
    return id;
  }

  async syncNow(): Promise<void> {
    if (this.state.syncing || !navigator.onLine) return;
    this.setState({ syncing: true });
    const items = (await getAllItems())
      .filter((i) => i.status === 'pending' || i.status === 'failed')
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

    let synced = 0;
    let failed = 0;

    for (const item of items) {
      if (item.id === undefined) continue;
      try {
        item.status = 'syncing';
        item.last_attempt_at = new Date().toISOString();
        await updateItem(item);
        await this.executeSyncItem(item);
        await deleteItem(item.id);
        synced += 1;
      } catch (error) {
        item.retry_count += 1;
        item.status = item.retry_count >= MAX_RETRIES ? 'failed' : 'pending';
        item.error_message = error instanceof Error ? error.message : 'Sync failed';
        await updateItem(item);
        failed += 1;
      }
    }

    await this.refreshPendingCount();
    this.setState({
      syncing: false,
      lastMessage: synced > 0 && failed === 0
        ? 'تمت المزامنة بنجاح'
        : failed > 0
          ? `فشل مزامنة ${failed} عملية`
          : this.state.lastMessage,
    });
  }

  private async executeSyncItem(item: OfflineQueueItem): Promise<void> {
    const headers: Record<string, string> = {
      'X-Idempotency-Key': item.idempotency_key,
      ...(item.method !== 'GET' ? { 'Content-Type': 'application/json' } : {}),
    };

    const token = localStorage.getItem('access_token');
    if (token) headers.Authorization = `Bearer ${token}`;

    if (item.operation_type === 'complaint_submit' && item.attachments.length > 0) {
      const uploadedPaths: string[] = [];
      for (const attachment of item.attachments) {
        const formData = new FormData();
        formData.append('file', fromOfflineAttachment(attachment));
        const uploadResp = await fetch(`${API_BASE_URL}/uploads/public`, {
          method: 'POST',
          headers: {
            'X-Idempotency-Key': `${item.idempotency_key}-upload-${uploadedPaths.length + 1}`,
          },
          body: formData,
        });
        if (!uploadResp.ok) throw new Error('فشل مزامنة صورة الشكوى');
        const uploadData = await uploadResp.json();
        uploadedPaths.push(uploadData.path);
      }
      item.payload = {
        ...item.payload,
        ...(uploadedPaths.length > 0 ? { images: uploadedPaths } : {}),
      };
    }

    if (item.operation_type === 'task_update' && item.attachments.length > 0) {
      const uploadedPaths: string[] = Array.isArray(item.payload?.after_photos)
        ? [...item.payload.after_photos]
        : [];
      for (const attachment of item.attachments) {
        const formData = new FormData();
        formData.append('file', fromOfflineAttachment(attachment));
        const uploadResp = await fetch(`${API_BASE_URL}/uploads/?category=tasks`, {
          method: 'POST',
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            'X-Idempotency-Key': `${item.idempotency_key}-upload-${uploadedPaths.length + 1}`,
          },
          body: formData,
        });
        if (!uploadResp.ok) throw new Error('فشل مزامنة صورة بعد الإصلاح');
        const uploadData = await uploadResp.json();
        uploadedPaths.push(uploadData.path);
      }
      item.payload = {
        ...item.payload,
        after_photos: uploadedPaths,
      };
    }

    const resp = await fetch(`${API_BASE_URL}${item.endpoint}`, {
      method: item.method,
      headers,
      body: item.method === 'GET' ? undefined : JSON.stringify(item.payload),
    });

    if (!resp.ok) {
      if (TRANSIENT_HTTP_CODES.has(resp.status)) {
        throw new Error(`Transient sync error (${resp.status})`);
      }
      const text = await resp.text().catch(() => '');
      throw new Error(text || `Sync failed (${resp.status})`);
    }
  }
}

export const offlineSyncManager = new OfflineSyncManager();
