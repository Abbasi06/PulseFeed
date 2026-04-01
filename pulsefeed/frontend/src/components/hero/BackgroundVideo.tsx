import { useEffect, useRef } from "react";
import Hls from "hls.js";

interface BackgroundVideoProps {
  src: string;
}

export default function BackgroundVideo({ src }: BackgroundVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    let hls: Hls;
    const video = videoRef.current;

    if (video) {
      if (Hls.isSupported()) {
        hls = new Hls();
        hls.loadSource(src);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          video.play().catch(() => {
            // Auto-play was prevented by browser
          });
        });
      } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        // Fallback to native HLS support (Safari)
        video.src = src;
        video.addEventListener("loadedmetadata", () => {
          video.play().catch(() => {});
        });
      }
    }

    return () => {
      if (hls) {
        hls.destroy();
      }
    };
  }, [src]);

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden -z-10 -mt-[150px]">
      {/* Overlay to ensure Hero text readability */}
      <div className="absolute inset-0 bg-black/40 mix-blend-multiply z-10 pointer-events-none" />
      <video
        ref={videoRef}
        className="w-full h-full object-cover mix-blend-screen opacity-70"
        autoPlay
        loop
        muted
        playsInline
      />
    </div>
  );
}
