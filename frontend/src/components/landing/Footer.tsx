import { motion } from "framer-motion";
import PulseFeedIcon from "../PulseFeedIcon";

export default function Footer() {
  return (
    <footer className="w-full bg-[#010101] border-t border-white/5 py-12 font-sans relative z-10">
      <div className="container mx-auto px-6 max-w-7xl">
        <div className="flex flex-col md:flex-row justify-between items-center md:items-start gap-8">
          <div className="flex flex-col items-center md:items-start gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-[#B7397A] to-[#4C6E94] shadow-[0_0_15px_rgba(183,57,122,0.4)]">
                <PulseFeedIcon size={16} color="white" />
              </div>
              <span className="text-xl font-bold tracking-tight text-white">
                PulseFeed.ai
              </span>
            </div>
            <p className="text-sm text-white/50 max-w-xs text-center md:text-left">
              The intelligent knowledge feed for modern professionals.
            </p>
          </div>

          <div className="flex gap-12 text-sm text-center md:text-left">
            <div className="flex flex-col gap-3">
              <h5 className="font-semibold text-white tracking-wide mb-1">
                Product
              </h5>
              <a
                href="#"
                className="text-white/50 hover:text-white transition-colors"
              >
                Features
              </a>
              <a
                href="#"
                className="text-white/50 hover:text-white transition-colors"
              >
                Pricing
              </a>
              <a
                href="#"
                className="text-white/50 hover:text-white transition-colors"
              >
                Changelog
              </a>
            </div>
            <div className="flex flex-col gap-3">
              <h5 className="font-semibold text-white tracking-wide mb-1">
                Company
              </h5>
              <a
                href="#"
                className="text-white/50 hover:text-white transition-colors"
              >
                About
              </a>
              <a
                href="#"
                className="text-white/50 hover:text-white transition-colors"
              >
                Blog
              </a>
              <a
                href="#"
                className="text-white/50 hover:text-white transition-colors"
              >
                Contact
              </a>
            </div>
            <div className="flex flex-col gap-3">
              <h5 className="font-semibold text-white tracking-wide mb-1">
                Legal
              </h5>
              <a
                href="#"
                className="text-white/50 hover:text-white transition-colors"
              >
                Privacy
              </a>
              <a
                href="#"
                className="text-white/50 hover:text-white transition-colors"
              >
                Terms
              </a>
            </div>
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-white/30">
          <p>
            © {new Date().getFullYear()} PulseFeed.ai Inc. All rights reserved.
          </p>
          <div className="flex gap-4">
            <a href="#" className="hover:text-white/70 transition-colors">
              Twitter
            </a>
            <a href="#" className="hover:text-white/70 transition-colors">
              LinkedIn
            </a>
            <a href="#" className="hover:text-white/70 transition-colors">
              GitHub
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
