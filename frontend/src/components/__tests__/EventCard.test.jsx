import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import EventCard from "../EventCard";

const BASE_PROPS = {
  name: "PyCon US 2026",
  date: "2026-05-15",
  location: "Pittsburgh, PA",
  type: "Conference",
  url: "https://us.pycon.org",
  reason: "Largest Python conference in North America.",
  image_url: "",
  liked: false,
  onLike: vi.fn(),
};

describe("EventCard", () => {
  it("renders the event name", () => {
    render(<EventCard {...BASE_PROPS} />);
    expect(screen.getByText("PyCon US 2026")).toBeInTheDocument();
  });

  it("renders the date", () => {
    render(<EventCard {...BASE_PROPS} />);
    expect(screen.getByText("2026-05-15")).toBeInTheDocument();
  });

  it("renders the location", () => {
    render(<EventCard {...BASE_PROPS} />);
    expect(screen.getByText("Pittsburgh, PA")).toBeInTheDocument();
  });

  it('defaults location to "Online" when empty', () => {
    render(<EventCard {...BASE_PROPS} location="" />);
    expect(screen.getByText("Online")).toBeInTheDocument();
  });

  it("renders the event type badge", () => {
    render(<EventCard {...BASE_PROPS} />);
    expect(screen.getByText("Conference")).toBeInTheDocument();
  });

  it("does not render type badge when type is empty", () => {
    render(<EventCard {...BASE_PROPS} type="" />);
    expect(screen.queryByText("Conference")).not.toBeInTheDocument();
  });

  it("renders the reason", () => {
    render(<EventCard {...BASE_PROPS} />);
    expect(screen.getByText(/Largest Python conference/)).toBeInTheDocument();
  });

  it("does not render reason section when reason is empty", () => {
    render(<EventCard {...BASE_PROPS} reason="" />);
    expect(screen.queryByText(/Why this/)).not.toBeInTheDocument();
  });

  it("name is a link when url is a real URL", () => {
    render(<EventCard {...BASE_PROPS} />);
    const link = screen.getByRole("link", { name: "PyCon US 2026" });
    expect(link).toHaveAttribute("href", "https://us.pycon.org");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it('name is plain text when url is "#"', () => {
    render(<EventCard {...BASE_PROPS} url="#" />);
    expect(
      screen.queryByRole("link", { name: "PyCon US 2026" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("PyCon US 2026")).toBeInTheDocument();
  });

  it("renders the like button", () => {
    render(<EventCard {...BASE_PROPS} />);
    expect(screen.getByRole("button", { name: "Like" })).toBeInTheDocument();
  });

  it("shows unlike label when liked is true", () => {
    render(<EventCard {...BASE_PROPS} liked={true} />);
    expect(screen.getByRole("button", { name: "Unlike" })).toBeInTheDocument();
  });

  it("calls onLike when like button is clicked", async () => {
    const onLike = vi.fn();
    render(<EventCard {...BASE_PROPS} onLike={onLike} />);
    await userEvent.click(screen.getByRole("button", { name: "Like" }));
    expect(onLike).toHaveBeenCalledOnce();
  });

  it("renders fallback image when image_url is empty", () => {
    render(<EventCard {...BASE_PROPS} image_url="" />);
    // alt="" makes the img presentational in ARIA
    expect(screen.getByRole("presentation").src).toContain("picsum.photos");
  });

  it("uses provided image_url when present", () => {
    render(
      <EventCard {...BASE_PROPS} image_url="https://example.com/event.jpg" />,
    );
    expect(screen.getByRole("presentation")).toHaveAttribute(
      "src",
      "https://example.com/event.jpg",
    );
  });
});
