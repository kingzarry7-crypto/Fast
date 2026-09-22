"use client";

import React, { useMemo } from "react";

interface LinkifiedTextProps {
  text: string;
}

type Token =
  | { type: "text"; value: string }
  | { type: "link"; text: string; url: string }
  | { type: "image"; alt: string; url: string };

// Order matters: markdown image, then markdown link, then raw URL.
const TOKEN_REGEX =
  /!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s<>()"'\]]+)/g;

const TRAILING_PUNCT = /[.,;:!?]+$/;

function tokenize(text: string): Token[] {
  const tokens: Token[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  TOKEN_REGEX.lastIndex = 0;

  while ((match = TOKEN_REGEX.exec(text)) !== null) {
    const [full, imgAlt, imgUrl, linkText, linkUrl, rawUrl] = match;

    if (match.index > lastIndex) {
      tokens.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }

    if (imgUrl !== undefined) {
      tokens.push({ type: "image", alt: imgAlt || "image", url: imgUrl });
    } else if (linkUrl !== undefined) {
      tokens.push({ type: "link", text: linkText, url: linkUrl });
    } else if (rawUrl !== undefined) {
      const trimmed = rawUrl.replace(TRAILING_PUNCT, "");
      const trailing = rawUrl.slice(trimmed.length);
      tokens.push({ type: "link", text: trimmed, url: trimmed });
      if (trailing) tokens.push({ type: "text", value: trailing });
    }

    lastIndex = match.index + full.length;
  }

  if (lastIndex < text.length) {
    tokens.push({ type: "text", value: text.slice(lastIndex) });
  }

  return tokens;
}

export default function LinkifiedText({ text }: LinkifiedTextProps) {
  const tokens = useMemo(() => tokenize(text || ""), [text]);

  return (
    <>
      {tokens.map((tok, i) => {
        if (tok.type === "text") {
          return <React.Fragment key={i}>{tok.value}</React.Fragment>;
        }

        if (tok.type === "link") {
          return (
            <a
              key={i}
              href={tok.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-300 hover:text-cyan-200 underline underline-offset-2 break-all"
            >
              {tok.text}
            </a>
          );
        }

        // image (markdown ![alt](url))
        return (
          <span key={i} className="block my-3">
            <a
              href={tok.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block max-w-full"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={tok.url}
                alt={tok.alt}
                className="rounded-lg border border-cyan-500/20 max-w-full max-h-[420px] object-contain hover:border-cyan-400 transition-colors"
              />
            </a>
          </span>
        );
      })}
    </>
  );
}
