import { Check, CheckCircle2, ChevronDown, Contact, type LucideIcon, Megaphone, MessageSquareText, Smartphone } from "lucide-react";
import { useId, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { DASH_CARD, DASH_PRIMARY_BUTTON, DASH_SOFT } from "./dashboardStyles";

export interface SetupStep {
  key: string;
  label: string;
  description: string;
  /** Where the step's action button goes. */
  path: string;
  action: string;
  /** Shown with a green tick once the step is complete. */
  doneLabel: string;
  done: boolean;
  icon: LucideIcon;
}

export interface SetupFacts {
  whatsappConnected: boolean;
  templateApproved: boolean;
  hasContacts: boolean;
  hasCampaign: boolean;
}

/** The four real milestones between an empty workspace and a first sent campaign. */
export function buildSetupSteps(facts: SetupFacts): SetupStep[] {
  return [
    {
      key: "whatsapp",
      label: "Connect WhatsApp Business Account",
      description: "Add your WhatsApp Business Account (WABA) with its Meta system-user token, then sync its numbers.",
      path: "/channels/accounts",
      action: "Connect WhatsApp",
      doneLabel: "WhatsApp account connected",
      done: facts.whatsappConnected,
      icon: Smartphone,
    },
    {
      key: "template",
      label: "Get a Template Approved",
      description: "Meta must approve a message template before you can broadcast it to customers.",
      path: "/templates/new",
      action: "Create Template",
      doneLabel: "Template approved by Meta",
      done: facts.templateApproved,
      icon: MessageSquareText,
    },
    {
      key: "contacts",
      label: "Add Your Customers",
      description: "Add or import the customers you want to reach on WhatsApp.",
      path: "/contacts",
      action: "Add Contacts",
      doneLabel: "Contacts added",
      done: facts.hasContacts,
      icon: Contact,
    },
    {
      key: "campaign",
      label: "Launch Your First Campaign",
      description: "Send an approved template to a group of customers and track replies.",
      path: "/campaigns/new",
      action: "Create Campaign",
      doneLabel: "Campaign created",
      done: facts.hasCampaign,
      icon: Megaphone,
    },
  ];
}

function WhatsAppGlyph(): JSX.Element {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="h-6 w-6 shrink-0" fill="currentColor">
      <path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.87 9.87 0 0 0 4.74 1.21h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2Zm0 18.15h-.01a8.2 8.2 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.23 8.25-8.23 2.2 0 4.27.86 5.82 2.42a8.18 8.18 0 0 1 2.41 5.83c0 4.54-3.7 8.22-8.23 8.22Zm4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.17.24-.64.8-.78.97-.15.16-.29.18-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.02-.38.11-.5.11-.11.25-.29.37-.43.13-.15.17-.25.25-.42.08-.16.04-.31-.02-.43-.06-.12-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.43h-.48a.92.92 0 0 0-.67.31c-.23.25-.87.85-.87 2.07 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.15-1.18-.06-.1-.23-.16-.48-.29Z" />
    </svg>
  );
}

function Chevron({ open }: { open: boolean }): JSX.Element {
  return (
    <span aria-hidden className="flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded-full border border-[#757575] text-black/55 dark:text-text-secondary">
      <ChevronDown className={`h-3 w-3 transition-transform duration-150 ${open ? "rotate-180" : ""}`} />
    </span>
  );
}

/** A collapsible region whose height animates and whose hidden content leaves the tab order. */
function Collapse({ open, id, children }: { open: boolean; id: string; children: ReactNode }): JSX.Element {
  return (
    <div id={id} className={`grid transition-[grid-template-rows] duration-150 ease-[cubic-bezier(0.4,0,0.2,1)] ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
      <div className={`min-h-0 overflow-hidden transition-[visibility] duration-150 ${open ? "visible" : "invisible"}`}>{children}</div>
    </div>
  );
}

/** One AiSensy-style step accordion: icon, bold title and chevron; expands to detail and action. */
function StepAccordion({ step, next, defaultOpen }: { step: SetupStep; next: boolean; defaultOpen: boolean }): JSX.Element {
  const [open, setOpen] = useState(defaultOpen);
  const bodyId = useId();
  const Icon = step.icon;
  return (
    <div className={`rounded-[8px] border border-transparent pb-2 pl-4 pt-2 transition-colors duration-150 ${next ? DASH_SOFT : "bg-surface"}`}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-12 w-full items-center gap-4 pr-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"
      >
        <span className="relative shrink-0">
          <span className={`flex h-[37px] w-[37px] items-center justify-center rounded-full ${next ? "bg-[#ffcc1d] text-[#0a474c]" : "text-[#2f4f4f] dark:text-text-secondary"}`}>
            <Icon aria-hidden className="h-[25px] w-[25px] p-[3px]" />
          </span>
          {step.done ? (
            <span className="absolute -bottom-0.5 -right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-surface text-[#27c152]">
              <CheckCircle2 aria-hidden className="h-5 w-5" />
            </span>
          ) : null}
        </span>
        <span className="min-w-0 flex-1 text-sm font-bold leading-[19px] text-[#2f4f4f] dark:text-text-primary">
          {step.label}
          {step.done ? <span className="sr-only"> (completed)</span> : null}
        </span>
        <Chevron open={open} />
      </button>
      <Collapse open={open} id={bodyId}>
        <div className="space-y-4 pb-2 pl-4 pr-4 pt-3">
          <p className="text-sm leading-[21px] text-[#6e6e6e] dark:text-text-secondary">{step.description}</p>
          {step.done ? (
            <p className="flex items-center gap-2 text-sm text-[#4a4a4a] dark:text-text-secondary">
              <CheckCircle2 aria-hidden className="h-6 w-6 text-[#27c152]" />
              {step.doneLabel}
            </p>
          ) : (
            <Link to={step.path} className={DASH_PRIMARY_BUTTON}>{step.action}</Link>
          )}
        </div>
      </Collapse>
    </div>
  );
}

/** AiSensy's "Setup FREE WhatsApp Business Account" card, driven by real workspace facts. */
export function SetupChecklist({ steps }: { steps: SetupStep[] }): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const listId = useId();
  const remaining = steps.filter((step) => !step.done).length;
  const next = steps.find((step) => !step.done);

  return (
    <section aria-labelledby={`${listId}-title`} className={`${DASH_CARD} px-5 py-2.5`}>
      <div className="flex items-center justify-between gap-3 pb-4 pt-4">
        <h2 id={`${listId}-title`} className="flex items-center gap-1 text-xl font-normal leading-[23px] text-text-primary">
          <WhatsAppGlyph />
          Setup your WhatsApp workspace
        </h2>
        <p className="shrink-0 text-sm text-[#6e6e6e] dark:text-text-secondary">
          {remaining === 0 ? "All done" : `${remaining} ${remaining === 1 ? "step" : "steps"} left`}
        </p>
      </div>

      {next ? (
        <div>
          <p className={`ml-1.5 inline-block rounded-t-[8px] px-3 pt-1 text-xs font-semibold leading-[17px] text-[#247309] dark:text-success-on-soft ${DASH_SOFT}`}>
            NEXT
          </p>
          <StepAccordion key={next.key} step={next} next defaultOpen />
        </div>
      ) : (
        <p className={`flex items-center gap-2 rounded-[8px] p-2.5 text-[15px] font-semibold text-[#2f4f4f] dark:text-text-primary ${DASH_SOFT}`}>
          <Check aria-hidden className="h-5 w-5 text-[#27c152]" />
          Your workspace is fully set up.
        </p>
      )}

      <Collapse open={expanded} id={listId}>
        <ol aria-label="All setup steps" className="space-y-1 pt-2">
          {steps.map((step) => (
            <li key={step.key}>
              <StepAccordion step={step} next={false} defaultOpen={false} />
            </li>
          ))}
        </ol>
      </Collapse>

      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={listId}
        onClick={() => setExpanded((value) => !value)}
        className="mt-1 flex items-center gap-3 rounded-md py-3 text-sm text-[#4a4a4a] transition-colors duration-200 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-text-secondary"
      >
        {expanded ? "Show less" : "All Steps"}
        <Chevron open={expanded} />
      </button>
    </section>
  );
}
