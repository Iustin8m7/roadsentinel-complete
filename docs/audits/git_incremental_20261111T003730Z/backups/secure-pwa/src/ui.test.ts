import { describe, expect, it } from "vitest";

import { redactionChipKind } from "./ui";

describe("redactionChipKind", () => {
  it("shows exactly what the API reports and never assumes redaction", () => {
    expect(redactionChipKind("full")).toBe("redacted");
    expect(redactionChipKind("heads_only")).toBe("redacted_heads");
    expect(redactionChipKind("off")).toBe("unredacted");
    expect(redactionChipKind("unknown")).toBe("warn");
    expect(redactionChipKind(undefined)).toBe("warn");
  });
});
