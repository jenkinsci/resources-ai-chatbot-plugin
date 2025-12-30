import type { Message } from "../model/Message";
import { Document, Packer, Paragraph } from "docx";
import jsPDF from "jspdf";

/* -------------------------
   Shared download helper
-------------------------- */

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

/* -------------------------
   TXT Export
-------------------------- */

export const exportAsTxt = (messages: Message[]) => {
  const content = messages.map((m) => `${m.sender}: ${m.text}`).join("\n\n");

  const blob = new Blob([content], { type: "text/plain" });
  downloadBlob(blob, "chat.txt");
};

/* -------------------------
   Markdown Export
-------------------------- */

export const exportAsMd = (messages: Message[]) => {
  const content = messages
    .map((m) => `${m.sender}: ${m.text}`)
    .join("\n\n");

  const blob = new Blob([content], { type: "text/markdown" });
  downloadBlob(blob, "chat.md");
};

/* -------------------------
   DOCX Export
-------------------------- */

export const exportAsDocx = async (messages: Message[]) => {
  const doc = new Document({
    sections: [
      {
        children: messages.map((m) => new Paragraph(`${m.sender}: ${m.text}`)),
      },
    ],
  });

  const blob = await Packer.toBlob(doc);
  downloadBlob(blob, "chat.docx");
};

/* -------------------------
   PDF Export
-------------------------- */

export const exportAsPdf = (messages: Message[]) => {
  const pdf = new jsPDF();
  // Basic layout settings
  const marginLeft = 10;
  const marginTop = 10;
  const marginBottom = 10;
  const lineHeight = 10;
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const maxLineWidth = pageWidth - marginLeft * 2;
  let y = marginTop;
  messages.forEach((m) => {
    const messageText = `${m.sender}: ${m.text}`;
    const wrappedLines = pdf.splitTextToSize(messageText, maxLineWidth);
    wrappedLines.forEach((line: string) => {
      // Add a new page if we are beyond the printable area
      if (y + lineHeight > pageHeight - marginBottom) {
        pdf.addPage();
        y = marginTop;
      }
      pdf.text(line, marginLeft, y);
      y += lineHeight;
    });
  });

  pdf.save("chat.pdf");
};
