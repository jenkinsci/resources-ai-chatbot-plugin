import type { Config } from "jest";

const config: Config = {
  verbose: true,
  testEnvironment: "jsdom",
  transform: {
    "^.+\\.tsx?$": "ts-jest",
  },

  globals: {
    "ts-jest": {
      tsconfig: "<rootDir>/tsconfig.app.json",
    },
  },
  setupFilesAfterEnv: ["<rootDir>/src/tests/setupTests.ts"],
};

export default config;
