import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/components/ui/tabs';
import { Spinner, TreeStructure, ListBullets, MapPin, CaretDown, CaretLeft, ChatCircleDots, ListChecks, FileText, WarningCircle, Plus } from '@phosphor-icons/react';
import { LocationFormDialog } from '@/components/LocationFormDialog';
import { GeoSubNav } from '@/components/GeoSubNav';

const LOCATION_TYPE_LABELS: Record<string, string> = {
  island: 'جزيرة',
  sector: 'قطاع',
  block: 'بلوك',
  building: 'مبنى',
  tower: 'برج',
  street: 'شارع',
  service_point: 'نقطة خدمة',
  other: 'أخرى',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'نشط',
  inactive: 'غير نشط',
  under_construction: 'قيد الإنشاء',
  demolished: 'مهدّم',
};

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-gray-100 text-gray-600',
  under_construction: 'bg-yellow-100 text-yellow-800',
  demolished: 'bg-red-100 text-red-800',
};

interface TreeNode {
  id: number;
  name: string;
  code: string;
  location_type: string;
  parent_id: number | null;
  status: string;
  is_active: number;
  children: TreeNode[];
  complaint_count: number;
  task_count: number;
  contract_count: number;
}

function TreeNodeComponent({ node, level = 0 }: { node: TreeNode; level?: number }) {
  const [expanded, setExpanded] = useState(level < 2);
  const hasChildren = node.children && node.children.length > 0;
  const totalOps = node.complaint_count + node.task_count;

  return (
    <div style={{ paddingRight: `${level * 20}px` }}>
      <div className="flex items-center gap-2 py-2 px-3 hover:bg-muted/50 rounded-md transition-colors group">
        <button
          className="w-5 h-5 flex items-center justify-center text-muted-foreground"
          onClick={() => setExpanded(!expanded)}
          disabled={!hasChildren}
        >
          {hasChildren ? (expanded ? <CaretDown size={14} /> : <CaretLeft size={14} />) : <span className="w-3.5" />}
        </button>
        <MapPin size={16} className="text-primary shrink-0" />
        <Link
          to={`/locations/${node.id}`}
          className="font-medium hover:text-primary transition-colors flex-1 min-w-0"
        >
          {node.name}
        </Link>
        <Badge variant="outline" className="text-xs shrink-0">
          {LOCATION_TYPE_LABELS[node.location_type] || node.location_type}
        </Badge>
        {totalOps > 0 && (
          <span className="text-xs text-muted-foreground shrink-0">
            {node.complaint_count > 0 && <span className="ml-2">📋{node.complaint_count}</span>}
            {node.task_count > 0 && <span className="ml-2">📌{node.task_count}</span>}
          </span>
        )}
        {node.contract_count > 0 && (
          <Badge variant="secondary" className="text-xs shrink-0">📄{node.contract_count}</Badge>
        )}
      </div>
      {expanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <TreeNodeComponent key={child.id} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function LocationsListPage() {
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [locations, setLocations] = useState<any[]>([]);
  const [stats, setStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('tree');
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // Filters
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [treeData, listData, statsData] = await Promise.all([
        apiService.getLocationTree(),
        apiService.getLocations({ is_active: 1 }),
        apiService.getLocationStats(),
      ]);
      setTree(treeData);
      setLocations(listData);
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load locations:', err);
    } finally {
      setLoading(false);
    }
  };

  // Filtered list
  const filteredLocations = useMemo(() => {
    let result = locations;
    if (search) {
      const term = search.toLowerCase();
      result = result.filter((loc: any) =>
        loc.name?.toLowerCase().includes(term) ||
        loc.code?.toLowerCase().includes(term) ||
        loc.description?.toLowerCase().includes(term)
      );
    }
    if (typeFilter) {
      result = result.filter((loc: any) => loc.location_type === typeFilter);
    }
    if (statusFilter) {
      result = result.filter((loc: any) => loc.status === statusFilter);
    }
    return result;
  }, [locations, search, typeFilter, statusFilter]);

  // Stats map for quick lookup
  const statsMap = useMemo(() => {
    const map: Record<number, any> = {};
    stats.forEach((s: any) => { map[s.location_id] = s; });
    return map;
  }, [stats]);

  // Summary cards
  const totalLocations = locations.length;
  const activeLocations = locations.filter((l: any) => l.status === 'active').length;
  const totalComplaints = stats.reduce((sum: number, s: any) => sum + (s.open_complaint_count || 0), 0);
  const totalDelayed = stats.reduce((sum: number, s: any) => sum + (s.delayed_task_count || 0), 0);
  const hotspots = stats.filter((s: any) => s.is_hotspot).length;

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin" size={32} />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <GeoSubNav active="locations" />
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">المواقع والجغرافيا التشغيلية</h1>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => setShowCreateDialog(true)}>
              <Plus size={16} className="ml-1" />
              إضافة موقع
            </Button>
            <Link to="/locations/reports">
              <Button variant="outline" size="sm">تقارير المواقع</Button>
            </Link>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold">{totalLocations}</div>
              <div className="text-xs text-muted-foreground">إجمالي المواقع</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-green-600">{activeLocations}</div>
              <div className="text-xs text-muted-foreground">مواقع نشطة</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-orange-600">{totalComplaints}</div>
              <div className="text-xs text-muted-foreground">شكاوى مفتوحة</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-red-600">{totalDelayed}</div>
              <div className="text-xs text-muted-foreground">مهام متأخرة</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-yellow-600">{hotspots}</div>
              <div className="text-xs text-muted-foreground">نقاط ساخنة</div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <Input
            placeholder="بحث بالاسم أو الرمز..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
          <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v === 'all' ? '' : v)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="نوع الموقع" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">جميع الأنواع</SelectItem>
              {Object.entries(LOCATION_TYPE_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v === 'all' ? '' : v)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="الحالة" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">جميع الحالات</SelectItem>
              {Object.entries(STATUS_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* View Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="tree" className="flex items-center gap-1">
              <TreeStructure size={16} />
              عرض شجري
            </TabsTrigger>
            <TabsTrigger value="list" className="flex items-center gap-1">
              <ListBullets size={16} />
              عرض جدول
            </TabsTrigger>
          </TabsList>

          {/* Tree View */}
          <TabsContent value="tree">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TreeStructure size={20} />
                  التسلسل الهرمي للمواقع
                </CardTitle>
              </CardHeader>
              <CardContent>
                {tree.length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">لا توجد مواقع مسجّلة</p>
                ) : (
                  <div className="space-y-0.5">
                    {tree.map((node) => (
                      <TreeNodeComponent key={node.id} node={node} />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Table View */}
          <TabsContent value="list">
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-right">الاسم</TableHead>
                      <TableHead className="text-right">الرمز</TableHead>
                      <TableHead className="text-right">النوع</TableHead>
                      <TableHead className="text-right">الحالة</TableHead>
                      <TableHead className="text-right">شكاوى</TableHead>
                      <TableHead className="text-right">مهام</TableHead>
                      <TableHead className="text-right">عقود</TableHead>
                      <TableHead className="text-right">متأخر</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredLocations.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                          لا توجد مواقع مطابقة
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredLocations.map((loc: any) => {
                        const s = statsMap[loc.id];
                        return (
                          <TableRow key={loc.id} className="cursor-pointer hover:bg-muted/50">
                            <TableCell>
                              <Link to={`/locations/${loc.id}`} className="font-medium hover:text-primary">
                                {loc.name}
                              </Link>
                            </TableCell>
                            <TableCell className="font-mono text-xs">{loc.code}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className="text-xs">
                                {LOCATION_TYPE_LABELS[loc.location_type] || loc.location_type}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <span className={`text-xs px-2 py-0.5 rounded ${STATUS_COLORS[loc.status] || ''}`}>
                                {STATUS_LABELS[loc.status] || loc.status}
                              </span>
                            </TableCell>
                            <TableCell>
                              {s?.open_complaint_count ? (
                                <span className="text-orange-600 font-medium">{s.open_complaint_count}</span>
                              ) : (
                                <span className="text-muted-foreground">0</span>
                              )}
                            </TableCell>
                            <TableCell>
                              {s?.open_task_count ? (
                                <span className="text-blue-600 font-medium">{s.open_task_count}</span>
                              ) : (
                                <span className="text-muted-foreground">0</span>
                              )}
                            </TableCell>
                            <TableCell>
                              {s?.active_contract_count ? (
                                <span className="text-green-600 font-medium">{s.active_contract_count}</span>
                              ) : (
                                <span className="text-muted-foreground">0</span>
                              )}
                            </TableCell>
                            <TableCell>
                              {s?.delayed_task_count ? (
                                <span className="text-red-600 font-bold flex items-center gap-1">
                                  <WarningCircle size={14} />
                                  {s.delayed_task_count}
                                </span>
                              ) : (
                                <span className="text-muted-foreground">0</span>
                              )}
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <LocationFormDialog
          open={showCreateDialog}
          onOpenChange={setShowCreateDialog}
          onSuccess={loadData}
        />
      </div>
    </Layout>
  );
}
