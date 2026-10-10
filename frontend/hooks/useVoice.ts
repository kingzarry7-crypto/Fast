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
  resultIndex?: number;
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
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);
  const [error, setError] = useState<string | null>(null);
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
    return () => {
      try { recognitionRef.current?.abort(); } catch { /* ignore */ }
      try {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") mediaRecorderRef.current.stop();
      } catch { /* ignore */ }
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
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

  // Low-latency speech path for live voice calls.
  // Browser speech starts as soon as the text arrives instead of waiting
  // for a complete ElevenLabs audio file to download.
  const speakInstant = useCallback(
    (text: string, overrideStyle?: VoiceStyle) => {
      const clean = cleanForSpeech(text);
      if (!clean) return;
      const mode = overrideStyle || styleRef.current;
      stop();
      speakBrowser(clean, mode);
    },
    [stop, speakBrowser]
  );

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

  const startBrowserRecording = useCallback(async (onResult: (text: string) => void) => {
    if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Voice recording is not supported in this browser. Please type your message or open the site in Safari.");
      return;
    }

    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      mediaChunksRef.current = [];
      const preferredType = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/ogg;codecs=opus",
      ].find((type) => MediaRecorder.isTypeSupported?.(type));
      const recorder = preferredType ? new MediaRecorder(stream, { mimeType: preferredType }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data?.size) mediaChunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        setError("The microphone recording failed. Check microphone permission and try again.");
        setListening(false);
      };
      recorder.onstop = async () => {
        const blob = new Blob(mediaChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        mediaChunksRef.current = [];
        mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
        mediaRecorderRef.current = null;
        setListening(false);
        if (blob.size < 100) {
          setError("I didn't receive any audio. Tap the microphone, allow access, and try speaking again.");
          return;
        }
        try {
          const extension = blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm";
          const result = await api.transcribeAudio(blob, `voice.${extension}`);
          if (!result.text?.trim()) {
            setError("I couldn't make out that recording. Please try again or type your message.");
            return;
          }
          onResult(result.text.trim());
        } catch (cause) {
          setError(cause instanceof Error ? cause.message : "Voice transcription failed. Please try again.");
        }
      };
      recorder.start();
      setListening(true);
    } catch (cause) {
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
      setListening(false);
      const reason = cause instanceof Error ? cause.name : "";
      setError(reason === "NotAllowedError" || reason === "SecurityError"
        ? "Microphone access is blocked. Allow microphone access for this site in your browser settings, then tap record again."
        : "Couldn't start the microphone. Check that no other app is using it and try again.");
    }
  }, []);

  const listen = useCallback((onResult: (text: string) => void, continuous = false) => {
    if (typeof window === "undefined") return;
    setError(null);
    const W = window as unknown as {
      SpeechRecognition?: new () => SpeechRecognitionInstance;
      webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
    };
    const SR = W.SpeechRecognition || W.webkitSpeechRecognition;
    if (!SR) {
      // Mobile browsers without Web Speech use the backend's configured STT providers.
      void startBrowserRecording(onResult);
      return;
    }
    try {
      recognitionRef.current?.abort();
    } catch {
      /* ignore */
    }

    const recognition = new SR();
    recognitionRef.current = recognition;
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = continuous;
    recognition.onresult = (e: SpeechRecognitionEvent) => {
      const start = continuous ? (e.resultIndex ?? 0) : 0;
      for (let i = start; i < e.results.length; i += 1) {
        const result = e.results[i];
        if (!result?.isFinal) continue;
        const transcript = result?.[0]?.transcript || "";
        if (transcript.trim()) onResult(transcript.trim());
      }
    };
    recognition.onerror = (event: unknown) => {
      setListening(false);
      const code = event && typeof event === "object" && "error" in event ? String((event as { error?: unknown }).error) : "";
      setError(code === "not-allowed" || code === "service-not-allowed"
        ? "Microphone access is blocked. Allow microphone access for this site and try again."
        : "Voice recognition stopped. Try recording again or type your message.");
    };
    recognition.onend = () => setListening(false);
    setListening(true);
    try {
      recognition.start();
    } catch {
      setListening(false);
      setError("Couldn't start voice recognition. Tap the microphone again or type your message.");
    }
  }, [startBrowserRecording]);

  const stopListening = useCallback(() => {
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      } else {
        recognitionRef.current?.stop();
        setListening(false);
      }
    } catch {
      setListening(false);
    }
  }, []);

  return {
    speak,
    speakInstant,
    stop,
    speaking,
    listening,
    listen,
    stopListening,
    listenContinuous: (onResult: (text: string) => void) => listen(onResult, true),
    supported,
    error,
    style,
    setVoiceStyle,
    voiceCharacter,
    setVoice,
    provider,
  };
}

export default useVoice;
