import Hero from '../components/hero/Hero';

export default function LandingPage() {
  return (
    <main className="bg-[#010101] min-h-screen w-full font-sans text-white">
      <Hero />
      
      {/* 
        Future Sections will be integrated below the Hero section.
      */}
      <section className="min-h-[50vh] flex flex-col items-center justify-center border-t border-white/5 bg-[#010101]">
         <p className="text-white/30 font-mono tracking-widest uppercase text-sm mb-4">Space reserved for next sections</p>
      </section>
    </main>
  );
}

