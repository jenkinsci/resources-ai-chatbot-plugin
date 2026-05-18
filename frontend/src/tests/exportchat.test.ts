import {
  exportAsTxt,
  exportAsMd,
  exportAsDocx,
  exportAsPdf,
} from "../utils/exportchat";
import { Document, Packer, Paragraph } from "docx";
import jsPDF from "jspdf";
import type { Message } from "../model/Message";

const textMock = jest.fn();
const addPageMock = jest.fn();
const saveMock = jest.fn();
const splitTextToSizeMock = jest.fn();

jest.mock("jspdf", () =>
  jest.fn().mockImplementation(() => ({
    text: textMock,
    addPage: addPageMock,
    save: saveMock,
    splitTextToSize: splitTextToSizeMock,
    internal: {
      pageSize: {
        getWidth: () => 200,
        getHeight: () => 40,
      },
    },
  })),
);

const messages: Message[] = [
  { id: "1", sender: "user", text: "hello" },
  { id: "2", sender: "jenkins-bot", text: "hi there" },
];

describe("exportchat", () => {
  const createObjectURLMock = jest.fn();
  const revokeObjectURLMock = jest.fn();
  let anchor: HTMLAnchorElement;
  let clickSpy: jest.SpyInstance;
  let createElementSpy: jest.SpyInstance;
  let blobCalls: { parts: BlobPart[]; options?: BlobPropertyBag }[];
  let originalBlob: typeof Blob;

  beforeAll(() => {
    URL.createObjectURL = createObjectURLMock;
    URL.revokeObjectURL = revokeObjectURLMock;

    originalBlob = global.Blob;
    (global as unknown as { Blob: unknown }).Blob = function (
      parts: BlobPart[],
      options?: BlobPropertyBag,
    ) {
      blobCalls.push({ parts, options });
      return new originalBlob(parts, options);
    };
  });

  afterAll(() => {
    (global as unknown as { Blob: unknown }).Blob = originalBlob;
  });

  beforeEach(() => {
    jest.clearAllMocks();
    blobCalls = [];
    createObjectURLMock.mockReturnValue("blob:mockurl");
    splitTextToSizeMock.mockImplementation((t: string) => [t]);

    anchor = document.createElement("a");
    clickSpy = jest.spyOn(anchor, "click").mockImplementation(() => {});
    createElementSpy = jest
      .spyOn(document, "createElement")
      .mockReturnValue(anchor);
  });

  afterEach(() => {
    createElementSpy.mockRestore();
    clickSpy.mockRestore();
  });

  describe("exportAsTxt", () => {
    it("exports plain text", () => {
      exportAsTxt(messages);

      expect(blobCalls).toHaveLength(1);
      expect(blobCalls[0].options?.type).toBe("text/plain");
      expect(blobCalls[0].parts).toEqual([
        "user: hello\n\njenkins-bot: hi there",
      ]);
      expect(anchor.download).toBe("chat.txt");
      expect(anchor.href).toBe("blob:mockurl");
      expect(clickSpy).toHaveBeenCalled();
      expect(revokeObjectURLMock).toHaveBeenCalledWith("blob:mockurl");
    });

    it("handles empty messages", () => {
      exportAsTxt([]);
      expect(blobCalls[0].parts).toEqual([""]);
    });
  });

  describe("exportAsMd", () => {
    it("exports markdown", () => {
      exportAsMd(messages);

      expect(blobCalls[0].options?.type).toBe("text/markdown");
      expect(blobCalls[0].parts).toEqual([
        "user: hello\n\njenkins-bot: hi there",
      ]);
      expect(anchor.download).toBe("chat.md");
    });

    it("handles empty messages", () => {
      exportAsMd([]);
      expect(blobCalls[0].parts).toEqual([""]);
    });
  });

  describe("exportAsDocx", () => {
    it("exports docx with one paragraph per message", async () => {
      await exportAsDocx(messages);

      expect(Paragraph).toHaveBeenCalledTimes(2);
      expect(Paragraph).toHaveBeenNthCalledWith(1, "user: hello");
      expect(Paragraph).toHaveBeenNthCalledWith(2, "jenkins-bot: hi there");
      expect(Packer.toBlob).toHaveBeenCalledTimes(1);
      expect(anchor.download).toBe("chat.docx");
    });

    it("handles empty messages", async () => {
      await exportAsDocx([]);

      expect(Paragraph).not.toHaveBeenCalled();
      const arg = (Document as unknown as jest.Mock).mock.calls[0][0];
      expect(arg.sections[0].children).toEqual([]);
    });
  });

  describe("exportAsPdf", () => {
    it("exports pdf", () => {
      exportAsPdf(messages);

      expect(jsPDF).toHaveBeenCalledTimes(1);
      expect(textMock).toHaveBeenCalledTimes(2);
      expect(textMock).toHaveBeenCalledWith("user: hello", 10, 10);
      expect(textMock).toHaveBeenCalledWith("jenkins-bot: hi there", 10, 20);
      expect(saveMock).toHaveBeenCalledWith("chat.pdf");
    });

    it("paginates when content overflows page height", () => {
      exportAsPdf([
        { id: "1", sender: "user", text: "a" },
        { id: "2", sender: "user", text: "b" },
        { id: "3", sender: "user", text: "c" },
      ]);

      expect(textMock).toHaveBeenCalledTimes(3);
      expect(addPageMock).toHaveBeenCalledTimes(1);
    });

    it("paginates wrapped lines from a single message", () => {
      splitTextToSizeMock.mockImplementationOnce(() => [
        "line1",
        "line2",
        "line3",
      ]);

      exportAsPdf([{ id: "1", sender: "user", text: "long" }]);

      expect(textMock).toHaveBeenCalledTimes(3);
      expect(addPageMock).toHaveBeenCalledTimes(1);
    });

    it("handles empty messages", () => {
      exportAsPdf([]);

      expect(textMock).not.toHaveBeenCalled();
      expect(saveMock).toHaveBeenCalledWith("chat.pdf");
    });
  });
});
