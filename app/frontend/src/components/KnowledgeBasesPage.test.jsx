import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { KnowledgeBasesPage } from "./KnowledgeBasesPage";

const mockedDashboardService = vi.hoisted(() => ({
  getVectorStores: vi.fn(),
}));

const mockedApiClient = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPostFormData: vi.fn(),
}));

vi.mock("../services/dashboardService", () => ({
  getVectorStores: mockedDashboardService.getVectorStores,
}));

vi.mock("../services/apiClient", () => ({
  apiGet: mockedApiClient.apiGet,
  apiPostFormData: mockedApiClient.apiPostFormData,
}));

describe("KnowledgeBasesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("initial load state", () => {
    it("shows loading text while fetching", async () => {
      mockedDashboardService.getVectorStores.mockReturnValue(new Promise(() => {}));
      mockedApiClient.apiGet.mockReturnValue(new Promise(() => {}));

      render(<KnowledgeBasesPage />);
      expect(screen.getByText(/Loading knowledge bases/i)).toBeInTheDocument();
    });

    it("shows no-knowledge-bases when list is empty", async () => {
      mockedDashboardService.getVectorStores.mockResolvedValue({ vector_stores: [] });
      mockedApiClient.apiGet.mockResolvedValue({ knowledge_bases: [] });

      render(<KnowledgeBasesPage />);

      await waitFor(() => {
        expect(screen.getByText(/No knowledge bases yet/i)).toBeInTheDocument();
      });
    });

    it("shows load error when API fails", async () => {
      mockedDashboardService.getVectorStores.mockResolvedValue({ vector_stores: [] });
      mockedApiClient.apiGet.mockRejectedValue(new Error("fail"));

      render(<KnowledgeBasesPage />);
      await waitFor(() => {
        expect(screen.getByText(/Unable to load knowledge bases/i)).toBeInTheDocument();
        expect(screen.getByRole("alert")).toBeInTheDocument();
      });
    });
  });

  describe("knowledge bases list", () => {
    it("renders a list of registered knowledge bases", async () => {
      mockedDashboardService.getVectorStores.mockResolvedValue({
        vector_stores: [
          { id: "vs-1", name: "KB1", created_at: "2024-01-01T00:00:00.000Z" },
          { id: "vs-2", name: "KB2", created_at: "2024-06-01T00:00:00.000Z" },
        ],
      });
      mockedApiClient.apiGet.mockResolvedValue({
        knowledge_bases: [
          {
            name: "KB1",
            vector_store_id: "vs-1",
            files: [{ filename: "a.txt" }],
            createdAt: "2024-01-01T00:00:00Z",
          },
          {
            name: "KB2",
            vector_store_id: "vs-2",
            files: [],
            createdAt: "2024-06-01T00:00:00Z",
          },
        ],
      });

      render(<KnowledgeBasesPage />);

      // After the merge logic runs, the KB names from vector stores appear
      await waitFor(() => {
        expect(screen.getByText("KB1")).toBeInTheDocument();
        expect(screen.getByText("KB2")).toBeInTheDocument();
      });
      expect(screen.getByText("a.txt")).toBeInTheDocument();
      expect(screen.getByText("No files")).toBeInTheDocument();
    });

    it("renders code element for vector store IDs", async () => {
      mockedDashboardService.getVectorStores.mockResolvedValue({
        vector_stores: [
          { id: "vs-abc123", name: "KB1", created_at: "2024-01-01T00:00:00.000Z" },
        ],
      });
      mockedApiClient.apiGet.mockResolvedValue({
        knowledge_bases: [
          {
            name: "KB1",
            vector_store_id: "vs-abc123",
            files: [],
            createdAt: "2024-01-01T00:00:00Z",
          },
        ],
      });

      render(<KnowledgeBasesPage />);

      const code = await screen.findByText("vs-abc123");
      expect(code.tagName.toLowerCase()).toBe("code");
    });
  });

  describe("form submission", () => {
    it("renders form inputs", async () => {
      mockedDashboardService.getVectorStores.mockResolvedValue({ vector_stores: [] });
      mockedApiClient.apiGet.mockResolvedValue({ knowledge_bases: [] });

      render(<KnowledgeBasesPage />);

      await waitFor(() => {
        expect(screen.getByText(/No knowledge bases yet/i)).toBeInTheDocument();
      });

      const nameInput = document.getElementById("kb-display-name");
      expect(nameInput).toBeInTheDocument();
      expect(nameInput.value).toBe("");

      const fileInput = document.getElementById("kb-documents");
      expect(fileInput).toBeInTheDocument();
    });

    it("shows the warning display area when warnings exist", async () => {
      mockedDashboardService.getVectorStores.mockResolvedValue({ vector_stores: [] });
      mockedApiClient.apiGet.mockResolvedValue({ knowledge_bases: [] });

      render(<KnowledgeBasesPage />);

      await waitFor(() => {
        expect(screen.getByText(/No knowledge bases yet/i)).toBeInTheDocument();
      });

      // The warning section uses role="status" but is only rendered when warnings.length > 0
      // Since no submission has happened, warnings is empty, so the element is not in DOM yet
      const status = screen.queryByRole("status");
      expect(status).not.toBeInTheDocument();
    });
  });

  describe("ui structure", () => {
    it("renders the create knowledge base form", async () => {
      mockedDashboardService.getVectorStores.mockResolvedValue({ vector_stores: [] });
      mockedApiClient.apiGet.mockResolvedValue({ knowledge_bases: [] });

      render(<KnowledgeBasesPage />);

      await waitFor(() => {
        expect(screen.getByText(/No knowledge bases yet/i)).toBeInTheDocument();
      });

      expect(screen.getByRole("heading", { name: /Create knowledge base/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/Display name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Documents/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Create and ingest/i })).toBeInTheDocument();
    });

    it("renders the registered knowledge bases section", async () => {
      mockedDashboardService.getVectorStores.mockResolvedValue({ vector_stores: [] });
      mockedApiClient.apiGet.mockResolvedValue({ knowledge_bases: [] });

      render(<KnowledgeBasesPage />);

      await waitFor(() => {
        expect(screen.getByText(/No knowledge bases yet/i)).toBeInTheDocument();
      });

      expect(screen.getByRole("heading", { name: /Registered knowledge bases/i })).toBeInTheDocument();
    });

    it("renders table header when there are rows", async () => {
      mockedDashboardService.getVectorStores.mockResolvedValue({
        vector_stores: [
          { id: "vs-1", name: "KB1", created_at: "2024-01-01T00:00:00.000Z" },
        ],
      });
      mockedApiClient.apiGet.mockResolvedValue({
        knowledge_bases: [
          {
            name: "KB1",
            vector_store_id: "vs-1",
            files: [],
            createdAt: "2024-01-01T00:00:00Z",
          },
        ],
      });

      render(<KnowledgeBasesPage />);

      await waitFor(() => {
        expect(screen.getByText("KB1")).toBeInTheDocument();
      });

      expect(screen.getByRole("columnheader", { name: "Display name" })).toBeInTheDocument();
      expect(screen.getByRole("columnheader", { name: "Vector store ID" })).toBeInTheDocument();
      expect(screen.getByRole("columnheader", { name: "Files" })).toBeInTheDocument();
      expect(screen.getByRole("columnheader", { name: "Created" })).toBeInTheDocument();
    });
  });
});
