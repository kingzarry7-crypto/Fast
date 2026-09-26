"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type VoiceStyle = "normal" | "fast" | "slow" | "human";

const RATE_MAP: Record<VoiceStyle, number> = {
  slow: 0.75,
  normal: 1.0,
  fast: 1.25,
  human: 0.95,
};

const PITCH_MAP: Record<VoiceStyle, number> = {
  slow: 0.95,
  normal: 1.0,
  fast: 1.05,
  human: 1.0,
};

interface SpeechRecognitionEvent {
  results: {
    length: number;
    [index: number]: {
      [index: number]: { transcript: string };
      isFinal: boolean;
    };
  };
}

interface SpeechRecognitionInstance {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: unknown) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

function cleanForSpeech(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/[*_#>~]/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 4000);
}

function pickVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  if (!voices.length) return null;
  return (
    voices.find((v) => /daniel|google uk english male|microsoft david/i.test(v.name)) ||
    voices.find((v) => /male/i.test(v.name) && v.lang.startsWith("en")) ||
    voices.find((v) => /samantha|google us english|microsoft aria|jenny/i.test(v.name)) ||
    voices.find((v) => v.lang.startsWith("en")) ||
    voices[0] ||
    null
  );
}

export function useVoice() {
  const [speaking, setSpeaking] = useState(false);
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(false);
  const [style, setStyle] = useState<VoiceStyle>("human");
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const styleRef = useRef<VoiceStyle>("human");
  styleRef.current = style;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const hasSynth = "speechSynthesis" in window;
    const hasRecog =
      "SpeechRecognition" in window || "webkitSpeechRecognition" in window;
    setSupported(hasSynth || hasRecog);
    if (hasSynth) {
      window.speechSynthesis.getVoices();
      const onVoices = () => window.speechSynthesis.getVoices();
      window.speechSynthesis.addEventListener("voiceschanged", onVoices);
      return () =>
        window.speechSynthesis.removeEventListener("voiceschanged", onVoices);
    }
  }, []);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("kz_voice_style") as VoiceStyle | null;
      if (saved && RATE_MAP[saved] != null) setStyle(saved);
    } catch {
      /* ignore */
    }
  }, []);

  const setVoiceStyle = useCallback((s: VoiceStyle) => {
    setStyle(s);
    styleRef.current = s;
    try {
      localStorage.setItem("kz_voice_style", s);
    } catch {
      /* ignore */
    }
  }, []);

  const speak = useCallback((text: string, overrideStyle?: VoiceStyle) => {
    if (typeof window === "undefined") return;
    if (!("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel();

    const clean = cleanForSpeech(text);
    if (!clean) return;

    const mode = overrideStyle || styleRef.current;
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.rate = RATE_MAP[mode] ?? 1;
    utterance.pitch = PITCH_MAP[mode] ?? 1;
    utterance.volume = 1;
    utterance.lang = "en-US";

    const voices = window.speechSynthesis.getVoices();
    const preferred = pickVoice(voices);
    if (preferred) utterance.voice = preferred;

    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);

    window.speechSynthesis.speak(utterance);
  }, []);

  const stop = useCallback(() => {
    if (typeof window === "undefined") return;
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, []);

  const listen = useCallback((onResult: (text: string) => void) => {
    if (typeof window === "undefined") return;
    const W = window as unknown as {
      SpeechRecognition?: new () => SpeechRecognitionInstance;
      webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
    };
    const SR = W.SpeechRecognition || W.webkitSpeechRecognition;
    if (!SR) return;

    try {
      recognitionRef.current?.abort();
    } catch {
      /* ignore */
    }

    const recognition = new SR();
    recognitionRef.current = recognition;
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = (e: SpeechRecognitionEvent) => {
      const transcript = e.results[0]?.[0]?.transcript || "";
      if (transcript) onResult(transcript);
    };
    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);

    setListening(true);
    try {
      recognition.start();
    } catch {
      setListening(false);
    }
  }, []);

  const stopListening = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch {
      /* ignore */
    }
    setListening(false);
  }, []);

  return {
    speak,
    stop,
    speaking,
    listening,
    listen,
    stopListening,
    supported,
    style,
    setVoiceStyle,
  };
}

export default useVoice;
