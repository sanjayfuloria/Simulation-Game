import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("Connection", "keep-alive");

  const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
  if (!OPENAI_API_KEY) {
    res.write(
      `data: ${JSON.stringify({ error: "OPENAI_API_KEY not set" })}\n\n`
    );
    res.end();
    return;
  }

  try {
    // Only accept POST from the consultation form
    if (req.method !== "POST") {
      res.status(405).write(
        `data: ${JSON.stringify({ error: "Method Not Allowed" })}\n\n`
      );
      res.end();
      return;
    }

    // Expect the client to POST JSON with these fields
    const { patient_name, date_of_visit, notes } = req.body || {};

    // Build a focused prompt for generating a medical consultation summary
    const systemMessage = `You are a medical scribe assistant. Produce a concise, professional clinical summary suitable for inclusion in a patient's chart. Use clear section headers (Summary, Assessment, Plan, Action Items, Patient Communication). Prioritize relevant findings, differential diagnoses if present, recommended follow-up, and clear next steps. Keep language clinical for the chart and also include a short patient-friendly message under 'Patient Communication'.`;

    const userMessage = `Patient: ${patient_name || "(unknown)"}\nDate of visit: ${date_of_visit || "(unknown)"}\n\nConsultation notes:\n${notes || "(no notes provided)"}\n\nPlease parse the notes and produce the structured summary.`;

    const payload: {
      model: string;
      messages: Array<{ role: string; content: string }>;
      max_tokens: number;
      stream: boolean;
    } = {
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: systemMessage },
        { role: "user", content: userMessage },
      ],
      max_tokens: 800,
      stream: true,
    };

    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${OPENAI_API_KEY}`,
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok || !response.body) {
      const text = await response.text();
      res.write(`data: ${JSON.stringify({ error: text })}\n\n`);
      res.end();
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      // `value` can sometimes be undefined in some stream implementations.
      // Guard the decode call to avoid passing undefined to TextDecoder (which throws).
      if (value) {
        buffer += decoder.decode(value, { stream: true });
      } else {
        // No data chunk this iteration; continue to next read.
        continue;
      }

      // OpenAI streams SSE-like chunks separated by \n\n and lines start with 'data: '
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || ""; // leftover

      for (const part of parts) {
        const line = part.trim();
        if (!line) continue;
        // each line may be like: data: {json}
        const matches = line.match(/data: ([\s\S]*)/);
        if (!matches) continue;
        const data = matches[1].trim();
        if (data === "[DONE]") {
          // signal done
          res.write(`event: done\n`);
          res.write(`data: [DONE]\n\n`);
          res.end();
          return;
        }

        try {
          const parsed = JSON.parse(data) as {
            choices?: Array<{ delta?: { content?: string } }>;
          };
          const delta = parsed.choices?.[0]?.delta?.content;
          if (delta) {
            // send the raw text chunk as an SSE data event
            res.write(`data: ${JSON.stringify({ chunk: delta })}\n\n`);
          }
        } catch {
          // Not JSON — forward raw
          res.write(`data: ${JSON.stringify({ chunk: data })}\n\n`);
        }
      }
    }

    // If stream ended without [DONE]
    res.write(`event: done\n`);
    res.write(`data: [DONE]\n\n`);
    res.end();
  } catch (err) {
    res.write(`data: ${JSON.stringify({ error: String(err) })}\n\n`);
    res.end();
  }
}
