import PulseFeedIcon from "../PulseFeedIcon";

export default function Footer() {
  return (
    <footer className="w-full bg-ink text-paper py-16 font-sans relative z-10">
      <div className="container mx-auto px-6 max-w-7xl">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 border-b-2 border-paper pb-16">
          <div className="col-span-1 md:col-span-1 flex flex-col items-center md:items-start gap-4 border-b-2 md:border-b-0 md:border-r-2 border-paper pb-8 md:pb-0 md:pr-8">
            <div className="flex items-center gap-3 bg-paper p-2 w-full justify-center md:justify-start">
              <PulseFeedIcon size={24} color="var(--color-ink)" />
              <span className="text-xl font-display font-bold tracking-tighter text-ink uppercase">
                PulseFeed
              </span>
            </div>
            <p className="font-mono text-[10px] uppercase font-bold tracking-widest leading-relaxed mt-4">
              Intelligence Feed // <br/> Vol.001
            </p>
          </div>

          <div className="col-span-1 md:col-span-3 grid grid-cols-2 md:grid-cols-3 gap-12 text-[10px] font-mono font-bold uppercase tracking-widest">
            <div className="flex flex-col gap-4">
              <h5 className="text-clay border-b border-paper pb-2 mb-2">
                [/] Infrastructure
              </h5>
              <a href="#" className="hover:text-clay transition-colors">
                Systems
              </a>
              <a href="#" className="hover:text-clay transition-colors">
                Pricing
              </a>
              <a href="#" className="hover:text-clay transition-colors">
                Telemetry
              </a>
            </div>
            
            <div className="flex flex-col gap-4">
              <h5 className="text-clay border-b border-paper pb-2 mb-2">
                [/] Entity
              </h5>
              <a href="#" className="hover:text-clay transition-colors">
                Manifesto
              </a>
              <a href="#" className="hover:text-clay transition-colors">
                Journal
              </a>
              <a href="#" className="hover:text-clay transition-colors">
                Comms
              </a>
            </div>
            
            <div className="flex flex-col gap-4 col-span-2 md:col-span-1">
              <h5 className="text-clay border-b border-paper pb-2 mb-2">
                [/] Compliance
              </h5>
              <a href="#" className="hover:text-clay transition-colors">
                Data Policy
              </a>
              <a href="#" className="hover:text-clay transition-colors">
                Terms of Service
              </a>
            </div>
          </div>
        </div>

        <div className="pt-8 flex flex-col md:flex-row items-center justify-between gap-4 text-[10px] font-mono font-bold uppercase tracking-widest text-paper/60">
          <p>
            © {new Date().getFullYear()} PULSEFEED.AI INC.
          </p>
          <div className="flex gap-8">
            <a href="#" className="hover:text-paper transition-colors">
              X/Twitter
            </a>
            <a href="#" className="hover:text-paper transition-colors">
              GitHub
            </a>
          </div>
        </div>

        {/* Terminal Shortcut Bar */}
        <div className="mt-8 pt-6 border-t border-paper/20 flex items-center justify-center gap-8 text-[10px] font-mono font-bold tracking-widest text-paper/40">
          <span>^H <span className="text-paper/70">HOME</span></span>
          <span>^P <span className="text-paper/70">PROCESS</span></span>
          <span>^S <span className="text-paper/70">SWARM</span></span>
          <span>^T <span className="text-clay">TOP ↑</span></span>
        </div>
      </div>
    </footer>
  );
}
