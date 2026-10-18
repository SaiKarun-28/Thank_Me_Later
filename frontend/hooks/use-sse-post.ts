'use client';

import { useCallback, useRef, useState } from 'react';

type EventHandler<T> = (data: T) => void;
type Handlers = { progress?: EventHandler<unknown>; source_status?: EventHandler<unknown>; result?: EventHandler<unknown>; error?: EventHandler<{ message?: string }>; };

function consume(buffer: string, handlers: Handlers): string {
  const packets = buffer.split(/\r?\n\r?\n/);
  const remainder = packets.pop() ?? '';
  for (const packet of packets) {
    let event = 'message'; const lines: string[] = [];
    for (const line of packet.split(/\r?\n/)) { if (line.startsWith('event:')) event = line.slice(6).trim(); if (line.startsWith('data:')) lines.push(line.slice(5).trim()); }
    if (!lines.length) continue;
    try { const data: unknown = JSON.parse(lines.join('\n')); const handler = handlers[event as keyof Handlers]; if (handler) handler(data as never); } catch { handlers.error?.({ message: 'Invalid streaming response received.' }); }
  }
  return remainder;
}

export function useSSEPost() {
  const controller = useRef<AbortController | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abort = useCallback(() => controller.current?.abort(), []);
  const post = useCallback(async (url: string, options: { body: BodyInit; headers?: HeadersInit; handlers: Handlers }) => {
    controller.current?.abort(); const signalController = new AbortController(); controller.current = signalController; setError(null); setIsStreaming(true);
    try {
      const response = await fetch(url, { method: 'POST', body: options.body, headers: options.headers, signal: signalController.signal });
      if (!response.ok || !response.body) throw new Error(`Request failed (${response.status}).`);
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
      while (true) { const { done, value } = await reader.read(); if (done) break; buffer = consume(buffer + decoder.decode(value, { stream: true }), options.handlers); }
      if (buffer.trim()) consume(`${buffer}\n\n`, options.handlers);
    } catch (reason) { if ((reason as DOMException).name !== 'AbortError') { const message = reason instanceof Error ? reason.message : 'Unexpected network error.'; setError(message); options.handlers.error?.({ message }); } }
    finally { setIsStreaming(false); }
  }, []);
  return { post, abort, isStreaming, error };
}
