export type ChatResponse = {
  answer: string;
  citations: string[];
  evidenceStrength: string;
  unsupportedClaims: string[];
};

export type ChatError = {
  error: 'validation_error' | 'rate_limited' | 'bedrock_unavailable' | 'source_unavailable' | string;
};

export async function askChatbot(sessionId: string, question: string): Promise<ChatResponse | ChatError> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionId,
      messages: [{ role: 'user', content: question }],
    }),
  });

  if (response.status === 429) {
    return { error: 'rate_limited' };
  }
  if (!response.ok) {
    return { error: 'bedrock_unavailable' };
  }
  return response.json() as Promise<ChatResponse | ChatError>;
}
