"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type RealtimeEvent = {
  type?: string;
  transcript?: string;
  delta?: string;
};

export function useRealtimeVoice() {
  const [supported, setSupported] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [active, setActive] = useState(false);
  const [muted, setMuted] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [listening, setListening] = useState(false);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const micRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const channelRef = useRef<RTCDataChannel | null>(null);
  const assistantTranscriptRef = useRef("");

  useEffect(() => {
    setSupported(
      typeof window !== "undefined" &&
        typeof RTCPeerConnection !== "undefined" &&
        !!navigator.mediaDevices?.getUserMedia
    );

    let cancelled = false;
    void api.getRealtimeStatus()
      .then((data) => {
        if (!cancelled) setEnabled(Boolean(data.enabled));
      })
      .catch(() => {
        if (!cancelled) setEnabled(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const cleanup = useCallback(() => {
    channelRef.current?.close();
    channelRef.current = null;

    pcRef.current?.close();
    pcRef.current = null;

    micRef.current?.getTracks().forEach((track) => track.stop());
    micRef.current = null;

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.srcObject = null;
      audioRef.current = null;
    }

    assistantTranscriptRef.current = "";
    setActive(false);
    setMuted(false);
    setSpeaking(false);
    setListening(false);
  }, []);

  const start = useCallback(
    async (
      conversationId: string | null | undefined,
      onTranscript?: (role: "user" | "assistant", text: string) => void
    ): Promise<boolean> => {
      if (!supported || !enabled || active) return false;

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const pc = new RTCPeerConnection();
        const channel = pc.createDataChannel("kz-events");

        const remoteAudio = new Audio();
        remoteAudio.autoplay = true;

        stream.getTracks().forEach((track) => pc.addTrack(track, stream));

        pc.ontrack = (event) => {
          const [remoteStream] = event.streams;
          if (!remoteStream) return;
          remoteAudio.srcObject = remoteStream;
          void remoteAudio.play().catch(() => undefined);
        };

        pc.onconnectionstatechange = () => {
          if (["failed", "closed", "disconnected"].includes(pc.connectionState)) {
            cleanup();
          }
        };

        channel.onopen = () => {
          setListening(true);
        };

        channel.onmessage = (event) => {
          try {
            const data = JSON.parse(String(event.data)) as RealtimeEvent;

            if (data.type === "input_audio_buffer.speech_started") {
              setListening(true);
              setSpeaking(false);
              return;
            }

            if (data.type === "response.audio.delta" || data.type === "response.output_audio.delta") {
              setSpeaking(true);
              setListening(false);
              return;
            }

            if (data.type === "response.audio.done" || data.type === "response.output_audio.done") {
              setSpeaking(false);
              setListening(true);
              return;
            }

            if (data.type === "conversation.item.input_audio_transcription.completed") {
              const text = String(data.transcript || "").trim();
              if (text) onTranscript?.("user", text);
              return;
            }

            if (data.type === "response.output_audio_transcript.delta") {
              assistantTranscriptRef.current += String(data.delta || "");
              return;
            }

            if (data.type === "response.output_audio_transcript.done") {
              const text = String(data.transcript || assistantTranscriptRef.current).trim();
              assistantTranscriptRef.current = "";
              if (text) onTranscript?.("assistant", text);
              return;
            }

            if (data.type === "response.done") {
              setSpeaking(false);
              setListening(true);
            }
          } catch {
            // Ignore malformed realtime events; the audio session can continue.
          }
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        if (pc.iceGatheringState !== "complete") {
          await new Promise<void>((resolve) => {
            const onIceGathering = () => {
              if (pc.iceGatheringState === "complete") {
                pc.removeEventListener("icegatheringstatechange", onIceGathering);
                resolve();
              }
            };
            pc.addEventListener("icegatheringstatechange", onIceGathering);
            window.setTimeout(() => {
              pc.removeEventListener("icegatheringstatechange", onIceGathering);
              resolve();
            }, 5000);
          });
        }

        const localSdp = pc.localDescription?.sdp;
        if (!localSdp) throw new Error("Could not create WebRTC offer");

        const answer = await api.startRealtimeCall(localSdp, conversationId);
        await pc.setRemoteDescription({ type: "answer", sdp: answer });

        pcRef.current = pc;
        micRef.current = stream;
        audioRef.current = remoteAudio;
        channelRef.current = channel;
        setMuted(false);
        setActive(true);
        setListening(true);
        return true;
      } catch {
        cleanup();
        return false;
      }
    },
    [active, cleanup, enabled, supported]
  );

  const toggleMute = useCallback(() => {
    const next = !muted;
    micRef.current?.getAudioTracks().forEach((track) => {
      track.enabled = !next;
    });
    setMuted(next);
    if (!next) setListening(true);
  }, [muted]);

  return {
    supported,
    enabled,
    active,
    muted,
    speaking,
    listening,
    start,
    stop: cleanup,
    toggleMute,
  };
}

export default useRealtimeVoice;
