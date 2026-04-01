import { useEffect, useRef } from "react";
import Hls from "hls.js";

interface HeroVideoProps {
  src: string;
  fallbackSrc?: string;
}

export default function HeroVideo({ src, fallbackSrc }: HeroVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    let hls: Hls | null = null;
    const video = videoRef.current;

    if (video) {
      if (Hls.isSupported()) {
        hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
        });
        hls.loadSource(src);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          video.play().catch((e) => console.log("Autoplay prevented:", e));
        });

        hls.on(Hls.Events.ERROR, function (event, data) {
          if (data.fatal) {
            console.warn("HLS Fatal Error. Falling back to MP4...", data);
            if (fallbackSrc) {
              video.src = fallbackSrc;
              video.play().catch(() => {});
            }
          }
        });
      } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        // Native Safari Support
        video.src = src;
        video.addEventListener("loadedmetadata", () => {
          video.play().catch(() => {});
        });
      } else if (fallbackSrc) {
        // Fallback if HLS totally unsupported (older browsers)
        video.src = fallbackSrc;
        video.play().catch(() => {});
      }
    }

    return () => {
      if (hls) {
        hls.destroy();
      }
    };
  }, [src, fallbackSrc]);

  return (
    <div className="relative w-full h-auto min-h-[500px] overflow-hidden">
      {/* 
         Video blending magic: 
         - mix-blend-screen ensures black background disappears into #010101
         - Overlay gradient fades it out smoothly into the rest of the dark page
      */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#010101] via-transparent to-[#010101] z-10 pointer-events-none" />

      <video
        ref={videoRef}
        className="w-full h-auto object-cover object-top mix-blend-screen opacity-90"
        autoPlay
        loop
        muted
        playsInline
      />
    </div>
  );
}
