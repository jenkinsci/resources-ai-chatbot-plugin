import fetchMock from "jest-fetch-mock";
import "@testing-library/jest-dom";

jest.mock("jspdf", () => {
  return jest.fn().mockImplementation(() => ({
    text: jest.fn(),
    save: jest.fn(),
  }));
});

jest.mock("docx", () => ({
  Document: jest.fn(),
  Packer: {
    toBlob: jest.fn(() => Promise.resolve(new Blob())),
  },
  Paragraph: jest.fn(),
}));

fetchMock.enableMocks();
