import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { TaskFilters } from "@/features/tasks/TaskFilters";
import { TaskTable } from "@/features/tasks/TaskTable";
import { TasksSectionForProfile } from "@/features/tasks/TasksSectionForProfile";
import type { Task, TaskListQuery } from "@/features/tasks/types";

const DAY = 86_400_000;

function taskFixture(overrides: Partial<Task> = {}): Task {
  return {
    id: "t1",
    contact_id: "c1",
    contact_name: "Ramesh K.",
    conversation_id: null,
    title: "Collect Aadhaar",
    task_type: "collect_documents",
    status: "open",
    priority: "high",
    due_at: new Date(Date.now() + DAY).toISOString(),
    has_time: true,
    reminder_at: null,
    description: null,
    assigned_agent_id: "u1",
    assigned_agent_name: "Priya S.",
    created_by: "u1",
    created_by_name: "Priya S.",
    completion_notes: null,
    completed_at: null,
    created_at: "2026-07-22T11:00:00Z",
    updated_at: "2026-07-22T11:00:00Z",
    row_version: 0,
    ...overrides,
  };
}

/** Each test gets an isolated client with retries off, so error states render immediately. */
function withProviders(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderTable(tasks: Task[], props: Partial<Parameters<typeof TaskTable>[0]> = {}) {
  return withProviders(
    <TaskTable
      tasks={tasks}
      selectedIds={new Set()}
      onToggle={vi.fn()}
      onToggleAll={vi.fn()}
      onEdit={vi.fn()}
      {...props}
    />,
  );
}

describe("TaskTable", () => {
  it("renders a task with its type, priority and customer link", () => {
    renderTable([taskFixture()]);

    expect(screen.getByText("Collect Aadhaar")).toBeInTheDocument();
    expect(screen.getByText("Collect documents")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ramesh K." })).toHaveAttribute(
      "href",
      "/contacts/c1",
    );
  });

  it("badges an overdue task", () => {
    renderTable([taskFixture({ due_at: new Date(Date.now() - 2 * DAY).toISOString() })]);
    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });

  it("badges a task due today", () => {
    const noon = new Date();
    noon.setHours(12, 0, 0, 0);
    renderTable([taskFixture({ due_at: noon.toISOString() })]);
    expect(screen.getByText("Due today")).toBeInTheDocument();
  });

  it("does not badge a completed task as overdue", () => {
    renderTable([
      taskFixture({
        status: "completed",
        due_at: new Date(Date.now() - 2 * DAY).toISOString(),
        completed_at: "2026-07-22T12:00:00Z",
      }),
    ]);
    expect(screen.queryByText("Overdue")).not.toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("offers Complete on an open task and Reopen on a terminal one", () => {
    const { unmount } = renderTable([taskFixture()]);
    expect(screen.getByRole("button", { name: "Complete" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reopen" })).not.toBeInTheDocument();
    unmount();

    renderTable([taskFixture({ status: "cancelled" })]);
    expect(screen.getByRole("button", { name: "Reopen" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete" })).not.toBeInTheDocument();
  });

  it("links to the conversation only when the task carries one", () => {
    const { unmount } = renderTable([taskFixture()]);
    expect(screen.queryByRole("link", { name: "Conversation" })).not.toBeInTheDocument();
    unmount();

    renderTable([taskFixture({ conversation_id: "conv1" })]);
    expect(screen.getByRole("link", { name: "Conversation" })).toHaveAttribute(
      "href",
      "/inbox?conversation=conv1",
    );
  });

  it("opens the edit dialog from the title", () => {
    const onEdit = vi.fn();
    renderTable([taskFixture()], { onEdit });
    fireEvent.click(screen.getByRole("button", { name: "Collect Aadhaar" }));
    expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ id: "t1" }));
  });

  it("selects a row and every row on the page", () => {
    const onToggle = vi.fn();
    const onToggleAll = vi.fn();
    renderTable([taskFixture()], { onToggle, onToggleAll });

    fireEvent.click(screen.getByLabelText("Select Collect Aadhaar"));
    fireEvent.click(screen.getByLabelText("Select all tasks on this page"));

    expect(onToggle).toHaveBeenCalledWith("t1");
    expect(onToggleAll).toHaveBeenCalled();
  });

  it("reveals a reschedule control without leaving the row", () => {
    renderTable([taskFixture()]);
    fireEvent.click(screen.getByRole("button", { name: "Reschedule" }));
    expect(screen.getByLabelText("New due date for Collect Aadhaar")).toBeInTheDocument();
  });
});

describe("TaskFilters", () => {
  function renderFilters(filters: TaskListQuery = {}) {
    const onChange = vi.fn();
    render(<TaskFilters filters={filters} onChange={onChange} />);
    return onChange;
  }

  it("emits the repeatable enum filters as single-element arrays", () => {
    const onChange = renderFilters();
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "completed" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ status: ["completed"] }));
  });

  it("clears an enum filter back to null", () => {
    const onChange = renderFilters({ priority: ["high"] });
    fireEvent.change(screen.getByLabelText("Priority"), { target: { value: "" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ priority: null }));
  });

  it("offers the completed_at sort the contract added", () => {
    renderFilters();
    const sort = screen.getByLabelText("Sort") as HTMLSelectElement;
    expect([...sort.options].map((option) => option.value)).toContain("-completed_at");
  });

  it("passes the search term through as q", () => {
    const onChange = renderFilters();
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "aadhaar" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ q: "aadhaar" }));
  });
});

describe("TasksSectionForProfile", () => {
  it("renders the section shell with an inline create action", () => {
    withProviders(<TasksSectionForProfile contactId="c1" />);

    expect(screen.getByRole("heading", { name: "Tasks" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New task" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show completed tasks" })).toBeInTheDocument();
  });

  it("opens the create dialog pre-bound to the contact", () => {
    withProviders(<TasksSectionForProfile contactId="c1" />);
    fireEvent.click(screen.getByRole("button", { name: "New task" }));

    const dialog = screen.getByRole("dialog", { name: "New task" });
    expect(within(dialog).getByLabelText("Title")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Create task" })).toBeInTheDocument();
  });
});
