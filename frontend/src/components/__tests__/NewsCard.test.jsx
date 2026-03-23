import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import NewsCard from "../NewsCard";

const BASE_PROPS = {
  title: "AI Reaches New Milestone",
  summary: "Researchers unveiled a major breakthrough in language models.",
  source: "Tech Weekly",
  url: "https://example.com/ai-news",
  topic: "AI",
  published_date: "2026-01-15",
  image_url: "",
  liked: false,
  onLike: vi.fn(),
};

describe("NewsCard", () => {
  it("renders the title", () => {
    render(<NewsCard {...BASE_PROPS} />);
    expect(screen.getByText("AI Reaches New Milestone")).toBeInTheDocument();
  });

  it("renders the summary", () => {
    render(<NewsCard {...BASE_PROPS} />);
    expect(screen.getByText(/Researchers unveiled/)).toBeInTheDocument();
  });

  it("renders the source", () => {
    render(<NewsCard {...BASE_PROPS} />);
    expect(screen.getByText("Tech Weekly")).toBeInTheDocument();
  });

  it("renders the topic badge", () => {
    render(<NewsCard {...BASE_PROPS} />);
    expect(screen.getByText("AI")).toBeInTheDocument();
  });

  it("title is a link when url is a real URL", () => {
    render(<NewsCard {...BASE_PROPS} />);
    const link = screen.getByRole("link", { name: "AI Reaches New Milestone" });
    expect(link).toHaveAttribute("href", "https://example.com/ai-news");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it('title is plain text when url is "#"', () => {
    render(<NewsCard {...BASE_PROPS} url="#" />);
    expect(
      screen.queryByRole("link", { name: "AI Reaches New Milestone" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("AI Reaches New Milestone")).toBeInTheDocument();
  });

  it("title is plain text when url is missing", () => {
    render(<NewsCard {...BASE_PROPS} url="" />);
    expect(
      screen.queryByRole("link", { name: "AI Reaches New Milestone" }),
    ).not.toBeInTheDocument();
  });

  it('does not render source when source is "Unknown"', () => {
    render(<NewsCard {...BASE_PROPS} source="Unknown" />);
    expect(screen.queryByText("Unknown")).not.toBeInTheDocument();
  });

  it("renders the like button", () => {
    render(<NewsCard {...BASE_PROPS} />);
    expect(screen.getByRole("button", { name: "Like" })).toBeInTheDocument();
  });

  it("shows unlike label when liked is true", () => {
    render(<NewsCard {...BASE_PROPS} liked={true} />);
    expect(screen.getByRole("button", { name: "Unlike" })).toBeInTheDocument();
  });

  it("calls onLike when like button is clicked", async () => {
    const onLike = vi.fn();
    render(<NewsCard {...BASE_PROPS} onLike={onLike} />);
    await userEvent.click(screen.getByRole("button", { name: "Like" }));
    expect(onLike).toHaveBeenCalledOnce();
  });

  it("renders fallback image when image_url is empty", () => {
    render(<NewsCard {...BASE_PROPS} image_url="" />);
    // alt="" makes the img presentational in ARIA
    const img = screen.getByRole("presentation");
    expect(img.src).toContain("picsum.photos");
  });

  it("uses provided image_url when present", () => {
    render(
      <NewsCard {...BASE_PROPS} image_url="https://example.com/photo.jpg" />,
    );
    expect(screen.getByRole("presentation")).toHaveAttribute(
      "src",
      "https://example.com/photo.jpg",
    );
  });

  it("renders General as default topic when topic is missing", () => {
    render(<NewsCard {...BASE_PROPS} topic="" />);
    expect(screen.getByText("General")).toBeInTheDocument();
  });
});
