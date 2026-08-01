# Private Vi Reactivation Operations Platform

**Status:** Final approved product scope  
**Product type:** Private internal software  
**Users:** Owner/Admin, Manager, 5–10 internal agents  
**Not a SaaS product:** No public signup, subscriptions, reseller system, or multi-project tenancy

## Product vision

A private WhatsApp CRM and Vi Reactivation Operations Platform designed for customer communication, KYC, SIM fulfilment, activation tracking, and enterprise team management.

Core positioning:

- AiSensy-like ease of use
- Respond.io-style team inbox
- HubSpot-style Customer 360
- Vi Reactivation domain workflows
- Enterprise operations and auditability
- Future compliant WhatsApp Scan module

---

# Final navigation

## 1. Executive Dashboard

- Revenue overview
- New leads
- Reactivation conversion
- Activation pending
- SIM delivery status
- KYC pending
- Campaign performance
- Agent performance
- Queue health
- SLA breaches
- Today’s tasks
- Recent activity

## 2. Inbox / Live Chat

- Active chats
- Unassigned chats
- Assigned chats
- Intervention requests
- Resolved chats
- Agent transfer
- Internal notes
- Tags
- Lead stage
- Customer attributes
- Quick replies
- Documents
- Customer 360 side panel

## 3. Chat History

- Complete conversation history
- Agent-wise history
- Date filters
- Customer search
- Media history
- Campaign-generated conversations
- Resolved chat records
- Audit trail

## 4. Contacts

- Add contact
- Import CSV
- Bulk actions
- Filters
- Segments
- Tags
- Assignment
- Opt-in status
- Lead stage
- Reactivation eligibility
- Duplicate detection
- Export

## 5. Customer 360

- Basic details
- Previous Vi number
- Active Delhi number
- Lead source
- Reactivation stage
- Eligibility result
- Conversation history
- Campaign history
- Internal notes
- Activity timeline
- KYC details
- Uploaded documents
- SIM order
- Activation status
- Agent ownership
- Reminders
- SLA
- Related family numbers

## 6. Campaigns

- Broadcast campaign
- CSV campaign
- Scheduled campaign
- API campaign
- Audience selection
- Segment selection
- Template selection
- Agent assignment
- Delivery report
- Read report
- Reply report
- Failed-message retry
- Campaign conversion
- Campaign-to-reactivation tracking

Excluded:

- Meta Ads Manager
- Ad creation
- Ad credits
- Facebook advertising setup

## 7. WhatsApp Templates

- Create template
- Draft
- Pending
- Approved
- Rejected / action required
- Text, image, video, and document templates
- Button templates
- Variable preview
- Sync with WhatsApp
- Favourite templates
- Template categories
- Template usage analytics
- AI template generator placeholder only

## 8. Segments

- Dynamic segments
- Static segments
- Saved filters
- Reactivation eligibility segment
- KYC pending segment
- Interested customers
- Documents pending
- Activation pending
- Completed customers
- Campaign engagement segments

## 9. Reactivation

### Dashboard

- Total uploaded numbers
- Eligibility pending
- Eligible numbers
- Interested customers
- KYC pending
- Documents received
- SIM ordered
- Activation pending
- Activated
- Failed / rejected cases

### Pipeline stages

1. New Lead
2. Follow-up
3. Interested
4. Eligibility Check
5. Eligible
6. Documents Pending
7. Documents Received
8. KYC Pending
9. Verification
10. Confirmed
11. SIM Order
12. Activation Pending
13. Completed
14. Not Eligible
15. Not Interested

### Features

- Kanban drag-and-drop
- Agent assignment
- Stage history
- Automatic reminders
- SLA tracking
- Notes
- Documents
- Eligibility reason
- Rejection reason
- Number reservation status
- Family-plan requirements
- Conversion tracking

## 10. KYC

- Customer KYC profile
- Original number-holder verification
- Delhi presence confirmation
- Active Delhi number verification
- Aadhaar/PAN document references
- Document checklist
- KYC appointment
- Verification status
- Rejection reason
- Manager approval
- Complete KYC audit history
- Restricted access and encryption for sensitive documents

## 11. Document Center

- Customer-wise documents
- KYC documents
- Identity proof
- Address proof
- SIM documents
- Eligibility documents
- Download permissions
- Document expiry
- Verification status
- Document notes
- Version history
- Audit trail

## 12. SIM Orders

- SIM order creation
- Customer address
- Assigned delivery agent
- Delivery status
- Dispatch date
- Delivery date
- Failed delivery reason
- SIM serial details
- Activation linkage
- Delhi NCR service area
- Delivery SLA
- Customer confirmation

## 13. WhatsApp Scan — Future module

- Upload number list
- Batch management
- Duplicate detection
- Scan queue
- Active-status result
- Business-account result
- Invalid-number result
- Export
- Create segment
- Scan analytics
- Retry failed scans

Only compliant and authorised methods are allowed. Unofficial WhatsApp Web bulk enumeration is excluded.

## 14. Simplified Automation

Pattern:

`Trigger → Conditions → Actions`

Examples:

- New lead → assign agent
- No response for 24 hours → reminder
- Documents pending → follow-up message
- KYC completed → move to verification
- SIM delivered → move to activation pending
- Activation completed → send confirmation
- Campaign reply → create lead
- SLA breach → notify manager
- Not interested → stop follow-ups
- Completed customer → archive workflow

## 15. Analytics

- Campaign analytics
- Conversation analytics
- Agent analytics
- Reactivation analytics
- Pipeline conversion
- Stage drop-off
- Lead source performance
- KYC turnaround time
- SIM delivery performance
- Activation success rate
- SLA performance
- Date-wise reports
- Agent comparison
- Exportable reports

## 16. Executive Reports

- Revenue
- Reactivation conversion
- Campaign ROI
- Team productivity
- Pending workload
- SLA violations
- Activation performance
- Customer acquisition source
- Daily / weekly / monthly reports
- Scheduled report delivery
- CSV / PDF export

## 17. Team Management

### Roles

- Owner
- Admin
- Manager
- Agent
- Read-only user

### Permissions

- Contact access
- Chat access
- Campaign creation
- Campaign approval
- KYC access
- Document download
- SIM management
- Reports
- API access
- Settings access

### Features

- Online status
- Agent workload
- Assignment rules
- Team performance
- Login history
- Permission audit

## 18. Tags and Attributes

- Custom tags
- Custom customer attributes
- Lead stage
- Number status
- Interest level
- Source
- Area
- Assigned agent
- Eligibility category
- KYC status
- Activation status
- Custom field types
- Required fields
- Active / inactive fields

## 19. Notifications

### Notification Center

- New chat
- New assignment
- Follow-up due
- KYC pending
- Document uploaded
- SIM delivery update
- Activation update
- SLA breach
- Campaign completed
- Approval request
- System alert

### Channels

- In-app
- Browser push
- Optional email
- Optional WhatsApp internal alert

## 20. Settings

- Business profile
- WhatsApp account
- Working hours
- Welcome message
- Off-hours message
- Chat assignment
- Auto-resolve
- Read receipt settings
- Campaign settings
- Opt-in / opt-out
- Tags
- Attributes
- Pipeline stages
- SLA rules
- Notification settings
- Roles and permissions
- Security
- Audit settings

## 21. Integrations — Limited

Keep:

- Google Sheets
- Webhooks

Future optional:

- Internal Vi systems
- Cloud storage
- Email
- Maps / delivery
- Custom reporting tools

Remove:

- Integration marketplace
- Shopify
- WooCommerce
- Razorpay
- PayU
- Promotional partner cards
- Unused integrations

## 22. API and Webhooks

- Contact API
- Campaign API
- Reactivation API
- Customer timeline API
- KYC status API
- SIM-order API
- Webhook subscriptions
- API keys
- Key permissions
- Usage logs
- IP restrictions
- Regenerate / revoke keys
- API documentation

---

# Enterprise features

## Global Search

Search customers, mobile numbers, chats, campaigns, documents, reactivation cases, SIM orders, notes, agents, and tags.

## Command Palette

Shortcut: `Ctrl + K`

Actions:

- Search customer
- Create contact
- Launch campaign
- Open live chat
- Add reactivation case
- Upload document
- Create task
- Open reports

## Audit Timeline

- Who changed what
- Old and new values
- Date and time
- Login / device
- Assignment changes
- Stage changes
- Document access
- Campaign actions
- Approval decisions

## Saved Views

- Contacts
- Campaigns
- Reactivation
- KYC
- SIM orders
- Reports
- Chat history

## Approval Workflow

- Large campaigns
- KYC approval
- Eligibility override
- SIM issue
- Activation completion
- Bulk exports
- Document downloads

## Download Center

- CSV exports
- Reports
- Campaign files
- Contact exports
- Scan results
- Generated documents
- Download status and history

---

# Design requirements

- Premium dark-green UI
- Dark mode
- Light mode
- Mobile responsive
- Compact information-dense tables
- Fast keyboard navigation
- Command palette
- Collapsible sidebar
- Customer 360 drawer
- Kanban pipeline
- Premium charts
- Skeleton loaders
- Clear empty states
- Notification badges
- Consistent modal / drawer system

---

# Permanently removed

- Ads Manager
- WhatsApp Payments
- SaaS subscription billing
- Plan upgrade pages
- Credit-purchase promotions
- Multi-project management
- Public signup
- Reseller management
- Integration marketplace
- Trial countdowns
- Schedule-demo promotions
- AiSensy promotional/help cards

---

# Implementation priority

## Phase 1 — Core Operations

- Dashboard
- Live Chat
- Chat History
- Contacts
- Customer 360
- Reactivation Pipeline
- KYC
- Documents
- SIM Orders
- Team
- Tags
- Notifications

## Phase 2 — Messaging and Growth

- Campaigns
- Templates
- Segments
- Analytics
- Simplified Automation
- Reports
- Google Sheets
- Webhooks

## Phase 3 — Enterprise and Future

- WhatsApp Scan
- API
- Approval workflows
- Advanced audit
- AI placeholders
- Executive intelligence
- Advanced mobile experience
