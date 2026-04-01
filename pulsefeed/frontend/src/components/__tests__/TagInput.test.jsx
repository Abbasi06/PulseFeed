import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import TagInput from "../TagInput";

// Controlled wrapper so we can test real state changes
function Wrapper({ initialTags = [], maxTags = 10, onChange }) {
  const [tags, setTags] = useState(initialTags);
  function handleChange(next) {
    setTags(next);
    onChange?.(next);
  }
  return <TagInput tags={tags} onChange={handleChange} maxTags={maxTags} />;
}

describe("TagInput", () => {
  // ---------------------------------------------------------------------------
  // Adding tags
  // ---------------------------------------------------------------------------

  it("adds a tag on Enter", async () => {
    render(<Wrapper />);
    await userEvent.type(screen.getByRole("textbox"), "Python{Enter}");
    expect(screen.getByText("Python")).toBeInTheDocument();
  });

  it("adds a tag on comma", async () => {
    render(<Wrapper />);
    await userEvent.type(screen.getByRole("textbox"), "React,");
    expect(screen.getByText("React")).toBeInTheDocument();
  });

  it("adds a tag on blur", async () => {
    render(<Wrapper />);
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "TypeScript");
    await userEvent.tab();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
  });

  it("clears the input after adding a tag", async () => {
    render(<Wrapper />);
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "Python{Enter}");
    expect(input).toHaveValue("");
  });

  // ---------------------------------------------------------------------------
  // Skipping invalid tags
  // ---------------------------------------------------------------------------

  it("ignores empty input on Enter", async () => {
    render(<Wrapper />);
    await userEvent.type(screen.getByRole("textbox"), "{Enter}");
    expect(screen.queryAllByRole("button", { name: /remove/i })).toHaveLength(
      0,
    );
  });

  it("ignores whitespace-only input", async () => {
    render(<Wrapper />);
    await userEvent.type(screen.getByRole("textbox"), "   {Enter}");
    expect(screen.queryAllByRole("button", { name: /remove/i })).toHaveLength(
      0,
    );
  });

  it("skips duplicate tag (same case)", async () => {
    render(<Wrapper initialTags={["Python"]} />);
    await userEvent.type(screen.getByRole("textbox"), "Python{Enter}");
    expect(screen.getAllByText("Python")).toHaveLength(1);
  });

  it("skips duplicate tag (different case)", async () => {
    render(<Wrapper initialTags={["python"]} />);
    await userEvent.type(screen.getByRole("textbox"), "Python{Enter}");
    expect(screen.getAllByText("python")).toHaveLength(1);
  });

  it("truncates tag to 50 characters", async () => {
    const long = "a".repeat(60);
    render(<Wrapper />);
    await userEvent.type(screen.getByRole("textbox"), `${long}{Enter}`);
    expect(screen.getByText("a".repeat(50))).toBeInTheDocument();
  });

  it("does not add a tag when maxTags is reached", async () => {
    const initial = ["a", "b", "c"];
    render(<Wrapper initialTags={initial} maxTags={3} />);
    await userEvent.type(screen.getByRole("textbox"), "new{Enter}");
    expect(screen.queryByText("new")).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Removing tags
  // ---------------------------------------------------------------------------

  it("removes a tag when × is clicked", async () => {
    render(<Wrapper initialTags={["Python", "React"]} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Remove Python" }),
    );
    expect(screen.queryByText("Python")).not.toBeInTheDocument();
    expect(screen.getByText("React")).toBeInTheDocument();
  });

  it("removes the last tag on Backspace when input is empty", async () => {
    render(<Wrapper initialTags={["Python", "React"]} />);
    await userEvent.click(screen.getByRole("textbox"));
    await userEvent.keyboard("{Backspace}");
    expect(screen.queryByText("React")).not.toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
  });

  it("does not remove a tag on Backspace when input has text", async () => {
    render(<Wrapper initialTags={["Python"]} />);
    await userEvent.type(screen.getByRole("textbox"), "ab{Backspace}");
    expect(screen.getByText("Python")).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // onChange callback
  // ---------------------------------------------------------------------------

  it("calls onChange with updated tags", async () => {
    const onChange = vi.fn();
    render(<Wrapper onChange={onChange} />);
    await userEvent.type(screen.getByRole("textbox"), "Go{Enter}");
    expect(onChange).toHaveBeenCalledWith(["Go"]);
  });

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  it("renders existing tags", () => {
    render(<Wrapper initialTags={["Python", "Go"]} />);
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("Go")).toBeInTheDocument();
  });

  it("shows placeholder when no tags", () => {
    render(<TagInput tags={[]} onChange={() => {}} placeholder="Add skill…" />);
    expect(screen.getByPlaceholderText("Add skill…")).toBeInTheDocument();
  });

  it("hides placeholder when tags exist", () => {
    render(
      <TagInput
        tags={["Python"]}
        onChange={() => {}}
        placeholder="Add skill…"
      />,
    );
    expect(screen.getByRole("textbox")).not.toHaveAttribute(
      "placeholder",
      "Add skill…",
    );
  });
});
