import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { WhatsAppQrConnect } from "@/features/whatsapp-qr";

/** QR-07 — the standalone WhatsApp Scan/Connect screen over the WAHA provider. */
export function WhatsAppQrPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Dashboard", to: "/" },
          { label: "WhatsApp", to: "/channels/accounts" },
          { label: "Scan to connect" },
        ]}
      />
      <PageHeader
        title="WhatsApp scan to connect"
        description="Pair a WhatsApp number by QR code and keep it connected."
      />
      <div className="mx-auto max-w-md">
        <WhatsAppQrConnect />
      </div>
    </PageContainer>
  );
}
