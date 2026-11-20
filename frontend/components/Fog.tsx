"use client";

import { useReducedMotion } from "framer-motion";
import { useEffect, useRef } from "react";

interface Mote {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  alpha: number;
  hue: "fog" | "spark";
}

/** Drifting fog banks plus a few ectoplasm sparks, drawn behind everything at low opacity. */
export function Fog() {
  const ref = useRef<HTMLCanvasElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let width = 0;
    let height = 0;
    let frame = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const motes: Mote[] = [];

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const seed = () => {
      motes.length = 0;
      const fogCount = Math.round(width / 90);
      for (let i = 0; i < fogCount; i++) {
        motes.push({
          x: Math.random() * width,
          y: height * (0.55 + Math.random() * 0.5),
          r: 120 + Math.random() * 220,
          vx: (Math.random() - 0.5) * 0.25,
          vy: (Math.random() - 0.5) * 0.04,
          alpha: 0.035 + Math.random() * 0.05,
          hue: "fog",
        });
      }
      for (let i = 0; i < 28; i++) {
        motes.push({
          x: Math.random() * width,
          y: Math.random() * height,
          r: 0.8 + Math.random() * 1.6,
          vx: (Math.random() - 0.5) * 0.15,
          vy: -0.1 - Math.random() * 0.25,
          alpha: 0.2 + Math.random() * 0.4,
          hue: "spark",
        });
      }
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      for (const m of motes) {
        if (m.hue === "fog") {
          const g = ctx.createRadialGradient(m.x, m.y, 0, m.x, m.y, m.r);
          g.addColorStop(0, `rgba(200, 195, 220, ${m.alpha})`);
          g.addColorStop(1, "rgba(200, 195, 220, 0)");
          ctx.fillStyle = g;
        } else {
          ctx.fillStyle = `rgba(124, 245, 165, ${m.alpha})`;
        }
        ctx.beginPath();
        ctx.arc(m.x, m.y, m.r, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    const step = () => {
      for (const m of motes) {
        m.x += m.vx;
        m.y += m.vy;
        if (m.hue === "spark" && m.y < -10) {
          m.y = height + 10;
          m.x = Math.random() * width;
        }
        if (m.x < -m.r) m.x = width + m.r;
        if (m.x > width + m.r) m.x = -m.r;
      }
      draw();
      frame = requestAnimationFrame(step);
    };

    resize();
    seed();
    if (reduced) {
      draw();
    } else {
      frame = requestAnimationFrame(step);
    }
    const onResize = () => {
      resize();
      seed();
      if (reduced) draw();
    };
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
    };
  }, [reduced]);

  return <canvas ref={ref} aria-hidden="true" className="pointer-events-none fixed inset-0 z-0" />;
}
