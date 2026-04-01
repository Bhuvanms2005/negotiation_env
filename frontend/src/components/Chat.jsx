import { useEffect, useRef } from "react"

export default function Chat({ messages }) {
  const bottomRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className="bg-gradient-to-br from-[#0f172a] to-[#020617] h-full p-6 rounded-2xl overflow-y-auto shadow-xl">
      {messages.map((msg, i) => (
        <div key={i} className={`mb-4 flex items-end ${msg.type === "ai" ? "justify-end" : "justify-start"}`}>
          
          {msg.type !== "ai" && (
            <div className="w-8 h-8 bg-gray-600 rounded-full mr-2"></div>
          )}

          <div className={`px-4 py-2 rounded-2xl max-w-xs ${
            msg.type === "ai"
              ? "bg-blue-600 text-white"
              : "bg-gray-700 text-white"
          }`}>
            <p className="text-sm">{msg.text}</p>
            {msg.price && (
              <p className="text-green-400 font-bold mt-1">₹{msg.price}</p>
            )}
          </div>

          {msg.type === "ai" && (
            <div className="w-8 h-8 bg-blue-500 rounded-full ml-2"></div>
          )}
        </div>
      ))}
      <div ref={bottomRef}></div>
    </div>
  )
}