"use client";

import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/api";

type RealtimeEvent = {
  type?: string;
  transcript?: string;
  item?: { content?: Array<{ transcript?: string }> };
  response?: { output?: Array<{ content?: Array<{ transcript?: string }> }> };
};

export function useRealtimeVoice(conversationId?: string | null) {
  const [active, setActive] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const channelRef = useRef<RTCDataChannel | null>(null);
  const conversationRef = useRef(conversationId);
  conversationRef.current = conversationId;

  const stop = useCallback(() => {
    channelRef.current?.close();
    channelRef.current = null;
    pcRef.current?.getSenders().forEach((sender) => {
      try { sender.track?.stop(); } catch { /* already stopped */ }
    });
    pcRef.current?.close();
    pcRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.srcObject = null;
      audioRef.current = null;
    }
    setActive(false);
    setConnecting(false);
  }, []);

  const start = useCallback(async () => {
    if (connecting || active) return;
    setError(null);
    setConnecting(true);
    let pc: RTCPeerConnection | null = null;
    let stream: MediaStream | null = null;
    try {
      const status = await api.getRealtimeStatus();
      if (!status.enabled) throw new Error("Live voice is not configured on the backend. Set OPENAI_API_KEY or OPENAI_REALTIME_API_KEY in Railway.");
      if (!navigator.mediaDevices?.getUserMedia || typeof RTCPeerConnection === "undefined") {
        throw new Error("This browser does not support live voice. Try the latest Chrome and allow microphone access.");
      }
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      streamRef.current = stream;
      pc = new RTCPeerConnection();
      pcRef.current = pc;
      stream.getTracks().forEach((track) => pc!.addTrack(track, stream!));
      pc.ontrack = (event) => {
        const audio = audioRef.current || new Audio();
        audioRef.current = audio;
        audio.autoplay = true;
        audio.srcObject = event.streams[0];
        void audio.play().catch(() => setError("Tap the live voice button again to allow audio playback."));
      };
      pc.onconnectionstatechange = () => {
        // "disconnected" can be transient on mobile networks; only tear down on failure.
        if (pc?.connectionState === "failed") {
          setError("Live voice connection failed. Check your network and tap to reconnect.");
          stop();
        }
      };
      const channel = pc.createDataChannel("oai-events");
      channelRef.current = channel;
      channel.onmessage = (event) => {
        try {
          const payload = JSON.parse(String(event.data)) as RealtimeEvent;
          if (payload.type === "error") {
            setError("Live voice reported an error. Check the OpenAI Realtime configuration in Railway.");
            return;
          }
          if (payload.type === "conversation.item.input_audio_transcription.completed") {
            const transcript = payload.transcript || payload.item?.content?.map((part) => part.transcript || "").join(" ").trim();
            if (transcript) void api.saveRealtimeTranscript(conversationRef.current, "user", transcript).catch(() => undefined);
          }
          if (payload.type === "response.audio_transcript.done") {
            const transcript = payload.transcript || payload.response?.output?.flatMap((item) => item.content || []).map((part) => part.transcript || "").join(" ").trim();
            if (transcript) void api.saveRealtimeTranscript(conversationRef.current, "assistant", transcript).catch(() => undefined);
          }
        } catch { /* ignore non-JSON events */ }
      };
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      if (pc.iceGatheringState !== "complete") {
        await new Promise<void>((resolve, reject) => {
          const timeout = window.setTimeout(() => {
            pc?.removeEventListener("icegatheringstatechange", onGathering);
            reject(new Error("Network setup timed out while preparing live voice. Check your connection and try again."));
          }, 10000);
          const onGathering = () => {
            if (pc?.iceGatheringState === "complete") {
              window.clearTimeout(timeout);
              pc?.removeEventListener("icegatheringstatechange", onGathering);
              resolve();
            }
          };
          pc?.addEventListener("icegatheringstatechange", onGathering);
        });
      }
      const offerSdp = pc.localDescription?.sdp;
      if (!offerSdp) throw new Error("The browser could not prepare a live voice connection.");
      const answer = await api.startRealtimeCall(offerSdp, conversationRef.current);
      await pc.setRemoteDescription({ type: "answer", sdp: answer });
      // SDP acceptance is not the same as a working audio connection. Wait for
      // WebRTC to connect so the UI doesn't claim live voice is active too early.
      await new Promise<void>((resolve, reject) => {
        if (pc?.connectionState === "connected") {
          resolve();
          return;
        }
        const timeout = window.setTimeout(() => {
          pc?.removeEventListener("connectionstatechange", onConnectionState);
          reject(new Error("Live voice did not connect in time. Check the backend and network, then try again."));
        }, 15000);
        const onConnectionState = () => {
          if (pc?.connectionState === "connected") {
            window.clearTimeout(timeout);
            pc?.removeEventListener("connectionstatechange", onConnectionState);
            resolve();
          } else if (pc?.connectionState === "failed" || pc?.connectionState === "closed") {
            window.clearTimeout(timeout);
            pc?.removeEventListener("connectionstatechange", onConnectionState);
            reject(new Error("Live voice connection failed. Check the backend and try again."));
          }
        };
        pc?.addEventListener("connectionstatechange", onConnectionState);
        onConnectionState();
      });
      setActive(true);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Could not start live voice.";
      setError(message);
      stop();
    } finally {
      setConnecting(false);
    }
  }, [active, connecting, stop]);

  const toggle = useCallback(() => {
    if (active || connecting) stop();
    else void start();
  }, [active, connecting, start, stop]);

  return { active, connecting, error, start, stop, toggle };
}
