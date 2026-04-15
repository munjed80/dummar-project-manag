# Dummar Project Management Platform - Product Requirements Document

A comprehensive platform for managing the Damascus Dummar Project, combining internal project management, electronic contract management, citizen complaints intake, and field task management with location-based operations.

**Experience Qualities**:
1. **Professional** - Government-grade interface that commands authority and trust through clean design and reliable functionality
2. **Accessible** - Mobile-first public portal ensuring every citizen can submit and track complaints effortlessly
3. **Efficient** - Streamlined workflows that minimize administrative overhead and accelerate decision-making

**Complexity Level**: Complex Application (advanced functionality, likely with multiple views)
This is a multi-tenant system with role-based access, geospatial features, workflow management, document handling, audit trails, and separate public/internal portals requiring sophisticated state management and data orchestration.

## Essential Features

### Authentication & Authorization
- **Functionality**: JWT-based authentication with role-based access control for 8 user types (project_director, contracts_manager, engineer_supervisor, complaints_officer, area_supervisor, field_team, contractor_user, citizen)
- **Purpose**: Secure access control ensuring users only see and modify data appropriate to their role
- **Trigger**: User navigates to login page and enters credentials
- **Progression**: Login form → JWT validation → Role check → Redirect to appropriate dashboard/portal
- **Success criteria**: Users can only access features permitted by their role; all protected routes verify JWT and permissions

### Citizen Complaints Portal
- **Functionality**: Public form for citizens to submit complaints with tracking number generation and status tracking
- **Purpose**: Transparent communication channel between citizens and project management
- **Trigger**: Citizen accesses public complaint submission page
- **Progression**: Fill form (name, phone, type, description, location, images) → Submit → Receive tracking number → Track status by number + phone
- **Success criteria**: Complaint stored in database, tracking number generated, citizen can retrieve status, staff can review and assign

### Field Tasks Management
- **Functionality**: Convert complaints to tasks or create internal tasks; assign to teams; track execution with before/after photos
- **Purpose**: Structured workflow from issue identification to resolution with visual proof
- **Trigger**: Staff creates task from complaint or manually; field team receives assignment
- **Progression**: Task creation → Assignment → Field team accepts → Upload before photos → Execute → Upload after photos → Complete → Review
- **Success criteria**: Full task lifecycle tracked, photo evidence stored, timeline/activity log maintained

### Contract Management
- **Functionality**: Complete contract CRUD with approval workflow, status tracking, QR verification, PDF generation
- **Purpose**: Digital transformation of contract lifecycle with audit trail
- **Trigger**: Contracts manager creates new contract
- **Progression**: Draft creation → Details entry → Document upload → Submit for review → Approval chain → Active status → Monitoring → Completion
- **Success criteria**: Contract data stored, approval trail immutable, QR code generates verification page, PDF summary available

### Location-Based Operations
- **Functionality**: Hierarchical location model (Area/Island → Building/Tower → Street/Zone) with PostGIS geometry support
- **Purpose**: Spatial organization of all operations for geographic analysis and assignment
- **Trigger**: Admin defines areas/islands; complaints/tasks/contracts linked to locations
- **Progression**: Import/create location data → Link records to locations → Filter/query by geography → Visualize on map
- **Success criteria**: PostGIS models support real boundary data, records queryable by location, map integration ready

### Director Dashboard
- **Functionality**: Real-time overview of complaints, tasks, contracts with counts, charts, recent activity, and map
- **Purpose**: Executive visibility into all project operations at a glance
- **Trigger**: Director logs in
- **Progression**: Dashboard loads → Fetch summary stats → Display charts → Show recent items → Render map markers
- **Success criteria**: Live data from database, meaningful KPIs, actionable recent activity list

### Audit & Reports
- **Functionality**: Immutable audit log for critical actions; filterable reports for complaints/tasks/contracts
- **Purpose**: Compliance, accountability, and data-driven decision making
- **Trigger**: Important action occurs (approval, status change); user requests report
- **Progression**: Action → Log entry created → Query audit log / Generate report → Filter by criteria → Export CSV/PDF
- **Success criteria**: All critical actions logged with user/timestamp, reports match database state, exports functional

## Edge Case Handling

- **Duplicate Complaints**: Track by phone + description similarity; show warning to staff
- **Expired Contracts**: Auto-flag contracts nearing end date; dashboard alert
- **Orphaned Tasks**: Tasks without assignee show in unassigned queue
- **Invalid Tracking Numbers**: Clear error message on tracking page
- **Upload Failures**: Retry mechanism with progress indication
- **Concurrent Edits**: Last-write-wins with updated_at timestamp check
- **Missing Location Data**: Allow complaints without island assignment; show "unassigned" filter
- **Role Changes**: Immediately reflect permission changes on next request
- **Deleted Users**: Preserve historical audit trail with [deleted user] indicator

## Design Direction

The design should evoke **governmental authority balanced with digital accessibility**. Think modern e-government platforms: professional, trustworthy, and efficient. The citizen portal must feel welcoming and simple, while the admin interface conveys capability and control. Arabic-first design with clear hierarchy and generous spacing ensures usability across literacy levels and device types.

## Color Selection

A professional palette that balances authority with approachability, rooted in civic trust.

- **Primary Color**: `oklch(0.45 0.12 240)` Deep Blue - Conveys governmental authority and trustworthiness
- **Secondary Colors**: 
  - `oklch(0.35 0.10 240)` Darker Blue - Navigation, headers, emphasis
  - `oklch(0.92 0.02 240)` Light Blue Grey - Backgrounds, cards
- **Accent Color**: `oklch(0.55 0.18 150)` Vibrant Green - Success states, CTAs, completed tasks
- **Foreground/Background Pairings**:
  - Primary Deep Blue (`oklch(0.45 0.12 240)`): White text (`oklch(1 0 0)`) - Ratio 8.2:1 ✓
  - Secondary Dark Blue (`oklch(0.35 0.10 240)`): White text (`oklch(1 0 0)`) - Ratio 11.5:1 ✓
  - Accent Green (`oklch(0.55 0.18 150)`): White text (`oklch(1 0 0)`) - Ratio 5.1:1 ✓
  - Background Light (`oklch(0.98 0.005 240)`): Dark text (`oklch(0.20 0.02 240)`) - Ratio 14.8:1 ✓
  - Warning Orange (`oklch(0.65 0.15 60)`): Dark text (`oklch(0.25 0.03 60)`) - Ratio 6.4:1 ✓
  - Destructive Red (`oklch(0.55 0.22 25)`): White text (`oklch(1 0 0)`) - Ratio 5.5:1 ✓

## Font Selection

Typography should communicate clarity and accessibility while maintaining professional authority appropriate for government services.

- **Primary Typeface**: Cairo - Modern Arabic font designed for digital interfaces with excellent readability at all sizes; supports both Arabic and Latin scripts harmoniously
- **Secondary Typeface**: IBM Plex Sans - For Latin text, code blocks, and technical content

- **Typographic Hierarchy**:
  - H1 (Page Titles): Cairo Bold / 32px / -0.02em tracking
  - H2 (Section Headers): Cairo SemiBold / 24px / -0.01em tracking
  - H3 (Card Headers): Cairo SemiBold / 18px / normal tracking
  - Body (Primary Content): Cairo Regular / 16px / normal tracking / 1.6 line-height
  - Small (Meta Info): Cairo Regular / 14px / normal tracking / 1.5 line-height
  - Captions (Timestamps): Cairo Regular / 12px / normal tracking / 1.4 line-height

## Animations

Animations should be **subtle and functional**, reinforcing user actions without delaying workflows. Use micro-interactions to provide feedback: button presses compress slightly (scale 0.98, 100ms), cards elevate on hover (shadow transition 200ms), status badges gently pulse when updated (opacity 0.7→1, 1s ease), and page transitions slide content with 300ms ease-out. Dashboard charts animate on load with staggered delays. Avoid decorative animations; every motion should communicate state change or guide attention.

## Component Selection

- **Components**:
  - **Dialog**: Contract approval workflow, task assignment modals
  - **Card**: Dashboard widgets, complaint/task/contract list items
  - **Table**: Filterable lists for complaints, tasks, contracts, users
  - **Form** + **Input** + **Label**: All data entry with react-hook-form + zod validation
  - **Select**: Status changes, role assignment, filter dropdowns
  - **Button**: Primary (green accent), Secondary (blue), Destructive (red), Ghost (neutral)
  - **Badge**: Status indicators (color-coded by state)
  - **Tabs**: Complaint details (info / timeline / photos)
  - **Calendar** + **Popover**: Date pickers for contracts and tasks
  - **Progress**: Contract completion percentage, task execution timeline
  - **Textarea**: Complaint descriptions, task notes
  - **Avatar**: User profile indicators in headers and audit logs
  - **Separator**: Section dividers in detail pages
  - **Alert**: Validation errors, success confirmations

- **Customizations**:
  - **FileUploadZone**: Custom drag-drop component for complaint images and task photos
  - **MapWidget**: Leaflet integration for location selection and visualization
  - **TimelineView**: Vertical activity log for tasks and contracts
  - **StatCard**: Dashboard metric cards with icon, value, change indicator
  - **FilterBar**: Sticky filter panel with date range, status, location selectors
  - **TrackingInput**: Special input for tracking number with format validation

- **States**:
  - Buttons: Default, hover (shadow lift), active (scale down), disabled (opacity 0.5), loading (spinner)
  - Inputs: Default, focused (ring-2 ring-primary), error (ring-destructive, error text below), disabled (bg-muted)
  - Cards: Default, hover (border-primary, subtle shadow), selected (border-primary border-2)

- **Icon Selection**:
  - Dashboard: `House`, `ChartBar`
  - Complaints: `ChatCircleDots`, `MagnifyingGlass`, `MapPin`
  - Tasks: `ListChecks`, `Camera`, `CalendarDot`
  - Contracts: `FileText`, `Signature`, `QrCode`
  - Users: `User`, `UserGear`, `Users`
  - Actions: `Plus`, `PencilSimple`, `Trash`, `Check`, `X`, `Download`, `Upload`
  - Navigation: `CaretLeft`, `CaretRight`, `List`
  - Status: `CheckCircle`, `Clock`, `Warning`, `XCircle`

- **Spacing**: Base unit 4px, component padding px-4 py-3, card padding p-6, section gaps gap-6, form field gaps gap-4, dashboard grid gap-4, page margins px-4 md:px-8

- **Mobile**: 
  - Tables collapse to stacked cards on <768px
  - Sidebar navigation becomes bottom tab bar on mobile
  - Multi-column dashboard becomes single column
  - Forms remain single column with full-width inputs
  - Filter bars collapse to expandable drawer
  - Map widgets get fullscreen toggle on mobile
