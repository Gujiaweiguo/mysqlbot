export interface ChatStreamPayload {
  code?: number
  msg?: string
  type?: string
  [key: string]: unknown
}

interface ConsumeChatStreamOptions<T extends ChatStreamPayload> {
  response: Response
  controller: AbortController
  isStopped: () => boolean
  onEvent: (event: T) => Promise<void> | void
  onMessageError?: (message: string) => void
  onDone?: () => void
  parseEvent?: (raw: string) => T
}

const parseChatEventChunks = (buffer: string): { chunks: string[]; remainder: string } => {
  const chunks = buffer.match(/data:.*}\n\n/g)
  if (!chunks) {
    return { chunks: [], remainder: buffer }
  }

  const consumed = chunks.join('')
  return {
    chunks,
    remainder: buffer.replace(consumed, ''),
  }
}

const defaultParseEvent = <T extends ChatStreamPayload>(raw: string): T => {
  return JSON.parse(raw.replace('data:{', '{')) as T
}

export const consumeChatStream = async <T extends ChatStreamPayload>(
  options: ConsumeChatStreamOptions<T>
): Promise<void> => {
  const reader = options.response.body?.getReader()
  if (!reader) {
    throw new Error('Response body is not readable')
  }

  const decoder = new TextDecoder('utf-8')
  const parseEvent = options.parseEvent ?? defaultParseEvent<T>
  let remainder = ''

  while (true) {
    if (options.isStopped()) {
      options.controller.abort()
      options.onDone?.()
      return
    }

    const { done, value } = await reader.read()
    if (done) {
      options.onDone?.()
      return
    }

    remainder += decoder.decode(value, { stream: true })
    const { chunks, remainder: nextRemainder } = parseChatEventChunks(remainder)
    remainder = nextRemainder

    if (chunks.length === 0) {
      continue
    }

    for (const chunk of chunks) {
      const event = parseEvent(chunk)
      if (event.code && event.code !== 200) {
        options.onMessageError?.(String(event.msg ?? 'Request error'))
        return
      }
      await options.onEvent(event)
    }
  }
}
