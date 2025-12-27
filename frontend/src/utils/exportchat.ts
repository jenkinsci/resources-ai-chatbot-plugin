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
  const content = messages
    .map((m) => `${m.sender}: ${m.text}`)
    .join("\n\n");

  const blob = new Blob([content], { type: "text/plain" });
  downloadBlob(blob, "chat.txt");
};

/* -------------------------
   Markdown Export
-------------------------- */

export const exportAsMd = (messages: Message[]) => {
  const content = messages
    .map((m) => `### ${m.sender}\n${m.text}`)
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
        children: messages.map(
          (m) => new Paragraph(`${m.sender}: ${m.text}`)
        ),
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
  let y = 10;

  messages.forEach((m) => {
    pdf.text(`${m.sender}: ${m.text}`, 10, y);
    y += 10;
  });

  pdf.save("chat.pdf");
};
