import { useState, ChangeEvent } from 'react'

interface Message {
  text: string
  image: File | null
}

const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState<string>('')
  const [image, setImage] = useState<File | null>(null)

  const handleSend = () => {
    const newMessage: Message = { text: input, image }
    setMessages([...messages, newMessage])
    setInput('')
    setImage(null)

    // Send message to backend or perform any other logic
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      setImage(files[0])
    } else {
      setImage(null)
    }
  }

  return (
    <div>
      <div>
        {messages.map((msg, idx) => (
          <div key={idx}>
            <p>{msg.text}</p>
            {msg.image && <img src={URL.createObjectURL(msg.image)} alt="Uploaded" />}
          </div>
        ))}
      </div>
      <input
        type="text"
        value={input}
        onChange={e => setInput(e.target.value)}
      />
      <input
        type="file"
        onChange={handleFileChange}
      />
      <button onClick={handleSend}>Send</button>
    </div>
  )
}

export default ChatInterface
