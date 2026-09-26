"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type TtsVoice } from "@/lib/api";

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
    .slice(0, 2000);
}

function pickVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  if (!voices.length) return null;
  return (
    voices.find((v) =>
      /daniel|google uk english male|microsoft david/i.test(v.name)
    ) ||
    voices.find((v) => /male/i.test(v.name) && v.lang.startsWith("en")) ||
    voices.find((v) => v.lang.startsWith("en")) ||
    voices[0] ||
    null
  );
}

export function useVoice() {
  const [speaking, setSpeaking] = useState(false);
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const [style, setStyle] = useState<VoiceStyle>("human");
  const [voiceCharacter, setVoiceCharacter] = useState<TtsVoice>("bella");
  const [provider, setProvider] = useState<"elevenlabs" | "browser">("elevenlabs");
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const styleRef = useRef<VoiceStyle>("human");
  const voiceRef = useRef<TtsVoice>("bella");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  styleRef.current = style;
  voiceRef.current = voiceCharacter;

  useEffect(() => {
    if (typeof window === "undefined") return;
    setSupported(true);
    if ("speechSynthesis" in window) {
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
      const savedVoice = localStorage.getItem("kz_voice_character") as TtsVoice | null;
      if (savedVoice === "bella" || savedVoice === "male") {
        setVoiceCharacter(savedVoice);
        voiceRef.current = savedVoice;
      }
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

  const setVoice = useCallback((v: TtsVoice) => {
    setVoiceCharacter(v);
    voiceRef.current = v;
    try {
      localStorage.setItem("kz_voice_character", v);
    } catch {
      /* ignore */
    }
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setSpeaking(false);
  }, []);

  const speakBrowser = useCallback((text: string, mode: VoiceStyle) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = RATE_MAP[mode] ?? 1;
    utterance.pitch = PITCH_MAP[mode] ?? 1;
    utterance.volume = 1;
    utterance.lang = "en-US";
    const preferred = pickVoice(window.speechSynthesis.getVoices());
    if (preferred) utterance.voice = preferred;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setProvider("browser");
  }, []);

  const speak = useCallback(
    async (text: string, overrideStyle?: VoiceStyle) => {
      const clean = cleanForSpeech(text);
      if (!clean) return;

      stop();

      const mode = overrideStyle || styleRef.current;
      abortRef.current = new AbortController();

      try {
        setSpeaking(true);
        setProvider("elevenlabs");
        const blob = await api.synthesizeSpeech(
          clean,
          mode,
          abortRef.current.signal,
          voiceRef.current
        );
        const url = URL.createObjectURL(blob);
        objectUrlRef.current = url;
        const audio = new Audio(url);
        audioRef.current = audio;
        audio.onended = () => {
          setSpeaking(false);
          if (objectUrlRef.current) {
            URL.revokeObjectURL(objectUrlRef.current);
            objectUrlRef.current = null;
          }
        };
        audio.onerror = () => {
          setSpeaking(false);
          speakBrowser(clean, mode);
        };
        await audio.play();
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          setSpeaking(false);
          return;
        }
        speakBrowser(clean, mode);
      }
    },
    [stop, speakBrowser]
  );

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
    voiceCharacter,
    setVoice,
    provider,
  };
}

export default useVoice;
