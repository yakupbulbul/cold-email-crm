"use client";

import { useState } from "react";
import { Cpu, Terminal, Wrench, AlertTriangle, Zap, BookOpen } from "lucide-react";
import CopyBlock from "@/components/ui/CopyBlock";
import { PageHeader, SurfaceCard } from "@/components/ui/primitives";

type ClientTab = "claude-code" | "cursor" | "generic";

const CLAUDE_CODE_CONFIG = `{
  "mcpServers": {
    "cold-email-crm": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/path/to/cold-email-crm/backend",
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}`;

const CURSOR_CONFIG = `{
  "mcpServers": {
    "cold-email-crm": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/path/to/cold-email-crm/backend",
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}`;

const GENERIC_COMMAND = `cd /path/to/cold-email-crm/backend && python -m app.mcp_server`;

const TOOL_CATEGORIES = [
  {
    name: "Campaigns",
    tools: [
      { name: "crm_list_campaigns", description: "List all campaigns with their status, mailbox, and execution summary.", params: "status?" },
      { name: "crm_get_campaign", description: "Get detailed information about a specific campaign including leads and sequence steps.", params: "campaign_id" },
      { name: "crm_create_campaign", description: "Create a new campaign with a name, mailbox, subject, and body.", params: "name, mailbox_id, subject, body" },
      { name: "crm_campaign_status", description: "Get campaign execution status: lead counts, send stats, blockers, and next scheduled action.", params: "campaign_id" },
    ],
  },
  {
    name: "Contacts",
    tools: [
      { name: "crm_list_contacts", description: "List contacts with optional filters. Returns email, name, status, verification, and tags.", params: "status?, limit?" },
      { name: "crm_create_contact", description: "Create a new contact with email and optional metadata.", params: "email, first_name?, last_name?, company?" },
      { name: "crm_search_contacts", description: "Search contacts by email pattern, company, or tags.", params: "query" },
    ],
  },
  {
    name: "Lists",
    tools: [
      { name: "crm_list_lists", description: "List all lead lists with contact counts.", params: "—" },
      { name: "crm_create_list", description: "Create a new lead list.", params: "name, description?" },
      { name: "crm_add_contacts_to_list", description: "Add contacts to a lead list by their IDs.", params: "list_id, contact_ids" },
    ],
  },
  {
    name: "Mailboxes",
    tools: [
      { name: "crm_list_mailboxes", description: "List all mailboxes with their status, SMTP health, and warm-up state.", params: "—" },
      { name: "crm_mailbox_status", description: "Get detailed status for a specific mailbox including SMTP check results and OAuth state.", params: "mailbox_id" },
      { name: "crm_smtp_check", description: "Run an SMTP connectivity check for a mailbox and return diagnostic results.", params: "mailbox_id" },
    ],
  },
  {
    name: "Sending",
    tools: [
      { name: "crm_send_email", description: "Send a single email through the backend SMTP pipeline. Uses the same send path as campaigns.", params: "mailbox_id, to, subject, body" },
      { name: "crm_send_logs", description: "Get recent send logs showing delivery status, SMTP responses, and timestamps.", params: "limit?, mailbox_id?" },
    ],
  },
  {
    name: "Deliverability",
    tools: [
      { name: "crm_deliverability_overview", description: "Get a comprehensive deliverability overview including domain readiness, mailbox health, and campaign stats.", params: "—" },
      { name: "crm_domain_readiness", description: "Check DNS readiness for a specific domain including MX, SPF, DKIM, and DMARC status.", params: "domain_id" },
    ],
  },
  {
    name: "Warm-up",
    tools: [
      { name: "crm_warmup_status", description: "Get warm-up engine status including global state, participating mailboxes, active pairs, health, and blockers.", params: "—" },
      { name: "crm_warmup_toggle", description: "Enable or disable global warm-up. When enabled, an immediate warm-up cycle is queued.", params: "enabled" },
      { name: "crm_warmup_mailbox_toggle", description: "Enable or disable warm-up participation for a specific mailbox.", params: "mailbox_id, enabled" },
      { name: "crm_warmup_logs", description: "Get recent warm-up activity logs.", params: "limit?" },
    ],
  },
  {
    name: "Health",
    tools: [
      { name: "crm_system_health", description: "Check overall system health including database, Redis, workers, and SMTP/IMAP providers.", params: "—" },
      { name: "crm_readiness_check", description: "Run production readiness checks covering configuration, infrastructure, and operational bounds.", params: "—" },
    ],
  },
];

export default function McpConnectorPage() {
  const [activeTab, setActiveTab] = useState<ClientTab>("claude-code");

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        eyebrow="Integration"
        title="MCP Connector"
        description="Connect Claude Code, Cursor, or any MCP-compatible client to control the CRM via natural language."
      />

      {/* Quick Start */}
      <SurfaceCard className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--primary)]/10">
            <Zap size={20} className="text-[var(--primary)]" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[var(--foreground)]">Quick Start</h2>
            <p className="text-sm text-[var(--muted-foreground)]">Add this JSON to your MCP client configuration file</p>
          </div>
        </div>
        <CopyBlock title="mcp.json" code={CLAUDE_CODE_CONFIG} />
        <p className="mt-3 text-xs text-[var(--muted-foreground)]">
          Replace <code className="rounded bg-[var(--surface-muted)] px-1.5 py-0.5 font-mono text-[var(--foreground)]">/path/to/cold-email-crm/backend</code> with the absolute path to your backend directory.
        </p>
      </SurfaceCard>

      {/* Prerequisites */}
      <SurfaceCard className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50">
            <BookOpen size={20} className="text-amber-600" />
          </div>
          <h2 className="text-lg font-bold text-[var(--foreground)]">Prerequisites</h2>
        </div>
        <ol className="space-y-2 text-sm text-[var(--foreground)] list-decimal list-inside">
          <li><span className="font-semibold">Python 3.11+</span> installed and available in PATH</li>
          <li><span className="font-semibold">Backend dependencies</span> installed (<code className="rounded bg-[var(--surface-muted)] px-1.5 py-0.5 font-mono text-xs">pip install -r requirements.txt</code>)</li>
          <li><span className="font-semibold">PostgreSQL</span> running and accessible (same DB as the web app)</li>
          <li><span className="font-semibold">Redis</span> running (required for cache and task queue)</li>
          <li><span className="font-semibold">Environment variables</span> configured (<code className="rounded bg-[var(--surface-muted)] px-1.5 py-0.5 font-mono text-xs">.env</code> in backend directory)</li>
        </ol>
      </SurfaceCard>

      {/* Client Configuration */}
      <SurfaceCard className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50">
            <Terminal size={20} className="text-blue-600" />
          </div>
          <h2 className="text-lg font-bold text-[var(--foreground)]">Configuration by Client</h2>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 rounded-xl bg-[var(--surface-muted)] p-1 mb-4">
          {([
            { id: "claude-code" as const, label: "Claude Code" },
            { id: "cursor" as const, label: "Cursor" },
            { id: "generic" as const, label: "Generic / CLI" },
          ]).map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${
                activeTab === tab.id
                  ? "bg-[var(--surface)] text-[var(--foreground)] shadow-sm"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "claude-code" && (
          <div className="space-y-3">
            <p className="text-sm text-[var(--muted-foreground)]">
              Add the following to your project&apos;s <code className="rounded bg-[var(--surface-muted)] px-1.5 py-0.5 font-mono text-xs text-[var(--foreground)]">.mcp.json</code> file in the repository root, or to <code className="rounded bg-[var(--surface-muted)] px-1.5 py-0.5 font-mono text-xs text-[var(--foreground)]">~/.claude/mcp.json</code> for global access.
            </p>
            <CopyBlock title=".mcp.json" code={CLAUDE_CODE_CONFIG} />
          </div>
        )}

        {activeTab === "cursor" && (
          <div className="space-y-3">
            <p className="text-sm text-[var(--muted-foreground)]">
              Create or edit <code className="rounded bg-[var(--surface-muted)] px-1.5 py-0.5 font-mono text-xs text-[var(--foreground)]">.cursor/mcp.json</code> in your project root.
            </p>
            <CopyBlock title=".cursor/mcp.json" code={CURSOR_CONFIG} />
          </div>
        )}

        {activeTab === "generic" && (
          <div className="space-y-3">
            <p className="text-sm text-[var(--muted-foreground)]">
              Any MCP client that supports stdio transport can connect by spawning the server process directly:
            </p>
            <CopyBlock title="Shell command" code={GENERIC_COMMAND} />
            <p className="text-sm text-[var(--muted-foreground)]">
              The server communicates via stdin/stdout using the MCP protocol. Set <code className="rounded bg-[var(--surface-muted)] px-1.5 py-0.5 font-mono text-xs text-[var(--foreground)]">PYTHONPATH=.</code> in the environment if running from outside the backend directory.
            </p>
          </div>
        )}
      </SurfaceCard>

      {/* Available Tools */}
      <SurfaceCard className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--primary)]/10">
            <Wrench size={20} className="text-[var(--primary)]" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[var(--foreground)]">Available Tools</h2>
            <p className="text-sm text-[var(--muted-foreground)]">22 tools across 8 categories</p>
          </div>
        </div>

        <div className="space-y-6">
          {TOOL_CATEGORIES.map((category) => (
            <div key={category.name}>
              <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-[var(--muted-foreground)]">
                {category.name} ({category.tools.length})
              </h3>
              <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border)] bg-[var(--surface-muted)]">
                      <th className="px-4 py-2.5 text-left font-semibold text-[var(--foreground)]">Tool</th>
                      <th className="px-4 py-2.5 text-left font-semibold text-[var(--foreground)]">Description</th>
                      <th className="px-4 py-2.5 text-left font-semibold text-[var(--foreground)]">Required Params</th>
                    </tr>
                  </thead>
                  <tbody>
                    {category.tools.map((tool, idx) => (
                      <tr key={tool.name} className={idx < category.tools.length - 1 ? "border-b border-[var(--border)]" : ""}>
                        <td className="px-4 py-2.5 font-mono text-xs font-semibold text-[var(--primary)] whitespace-nowrap">{tool.name}</td>
                        <td className="px-4 py-2.5 text-[var(--muted-foreground)]">{tool.description}</td>
                        <td className="px-4 py-2.5 font-mono text-xs text-[var(--foreground)] whitespace-nowrap">{tool.params}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </SurfaceCard>

      {/* Troubleshooting */}
      <SurfaceCard className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-50">
            <AlertTriangle size={20} className="text-red-600" />
          </div>
          <h2 className="text-lg font-bold text-[var(--foreground)]">Troubleshooting</h2>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
            <div className="font-semibold text-[var(--foreground)]">Connection refused / server won&apos;t start</div>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              Ensure PostgreSQL and Redis are running. The MCP server connects to the same database as the web application. Check that your <code className="rounded bg-[var(--surface)] px-1 py-0.5 font-mono text-xs">.env</code> file has valid <code className="rounded bg-[var(--surface)] px-1 py-0.5 font-mono text-xs">DATABASE_URL</code> and <code className="rounded bg-[var(--surface)] px-1 py-0.5 font-mono text-xs">REDIS_URL</code>.
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
            <div className="font-semibold text-[var(--foreground)]">ModuleNotFoundError: No module named &apos;app&apos;</div>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              The <code className="rounded bg-[var(--surface)] px-1 py-0.5 font-mono text-xs">cwd</code> must point to the <code className="rounded bg-[var(--surface)] px-1 py-0.5 font-mono text-xs">backend/</code> directory, and <code className="rounded bg-[var(--surface)] px-1 py-0.5 font-mono text-xs">PYTHONPATH</code> must include <code className="rounded bg-[var(--surface)] px-1 py-0.5 font-mono text-xs">.</code> so Python can resolve the <code className="rounded bg-[var(--surface)] px-1 py-0.5 font-mono text-xs">app</code> package.
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
            <div className="font-semibold text-[var(--foreground)]">Tools return empty or error results</div>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              The MCP tools query the same database as the web UI. If you see empty results, verify that data exists in the application first. For permission errors, ensure the database user has SELECT/INSERT access.
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
            <div className="font-semibold text-[var(--foreground)]">Server works locally but not in Docker</div>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              When running inside Docker, the MCP server is not exposed as a separate service. Connect from the host machine pointing <code className="rounded bg-[var(--surface)] px-1 py-0.5 font-mono text-xs">cwd</code> to your local checkout, not the container path. The server will connect to PostgreSQL via the host-mapped port.
            </p>
          </div>
        </div>
      </SurfaceCard>
    </div>
  );
}
