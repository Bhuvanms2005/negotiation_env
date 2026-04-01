import { useState } from "react"
import Chat from "./components/Chat"
import Dashboard from "./components/Dashboard"
import Reasoning from "./components/Reasoning"
import { resetEnv, stepEnv } from "./services/api"

export default function App() {
  const [messages, setMessages] = useState([])
  const [data, setData] = useState([])
  const [obs, setObs] = useState(null)
  const [mode, setMode] = useState("auto")
  const [input, setInput] = useState("")
  const [done, setDone] = useState(false)
  const [finalDeal, setFinalDeal] = useState(null)
  const [score, setScore] = useState(0)
  const [loading, setLoading] = useState(false)

  const calculateScore = (ai, client, steps) => {
    const profitScore = ai / client
    const efficiency = Math.max(0, 1 - steps * 0.1)
    return Math.min(1, (profitScore * 0.7 + efficiency * 0.3)).toFixed(2)
  }

  const startSimulation = async () => {
    const res = await resetEnv()
    setObs(res.data)
    setDone(false)
    setFinalDeal(null)
    setScore(0)

    setMessages([
      { type: "ai", text: "Hello! What's your budget?" }
    ])

    setData([])
  }

  const sendMessage = async () => {
    if (!input || !obs || done || loading) return

    setLoading(true)

    try {
      const res = await stepEnv(obs, mode, input, messages)

      const { observation, reward, action, done: isDone } = res.data

      const stepCount = messages.length + 1

      setMessages(prev => [
        ...prev,
        { type: "client", text: input },
        {
          type: "ai",
          text: action.message + " (" + (action.source || mode) + ")",
          price: action.price_offer
        }
      ])

      setData(prev => [
        ...prev,
        {
          step: Math.floor(prev.length / 2) + 1,
          reward,
          ai: action.price_offer,
          client: observation.client_budget
        }
      ])

      if (isDone) {
        setFinalDeal({
          ai: action.price_offer,
          client: observation.client_budget
        })

        setScore(
          calculateScore(
            action.price_offer,
            observation.client_budget,
            stepCount
          )
        )
      }

      setObs(observation)
      setDone(isDone)
      setInput("")
    } catch (err) {
      console.error(err)
    }

    setLoading(false)
  }

  return (
    <div className="bg-black text-white min-h-screen p-6 grid grid-cols-3 gap-6">

      <div className="col-span-2 flex flex-col gap-4 h-[80vh]">
        <Chat messages={messages} />
        <Reasoning text={done ? "Deal successfully closed" : "Negotiation in progress"} />
      </div>

      <div className="h-[80vh] flex flex-col gap-4">
        <Dashboard data={data} />

        {done && finalDeal && (
          <div className="bg-green-900 p-4 rounded-xl border border-green-500">
            <h2 className="text-lg font-bold mb-2">🎉 Deal Summary</h2>
            <p>Final AI Offer: ₹{finalDeal.ai}</p>
            <p>Client Final Budget: ₹{finalDeal.client}</p>
            <p className="mt-2 font-semibold text-green-300">
              Negotiation Score: {score}
            </p>
          </div>
        )}
      </div>

      <div className="col-span-3 flex flex-col gap-4">

        <div className="flex justify-between">
          <button
            onClick={startSimulation}
            className="bg-blue-600 px-4 py-2 rounded"
          >
            Start Negotiation
          </button>

          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="bg-gray-800 p-2 rounded"
          >
            <option value="auto">Auto</option>
            <option value="rule">Rule</option>
            <option value="gemini">Gemini</option>
          </select>
        </div>

        <div className="flex gap-4">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={done}
            placeholder={done ? "Negotiation completed ✔" : "Type your response..."}
            className="flex-1 p-3 bg-gray-800 rounded"
          />

          <button
            onClick={sendMessage}
            disabled={done || loading}
            className="bg-green-600 px-6 py-2 rounded"
          >
            {loading ? "Sending..." : "Send"}
          </button>
        </div>

      </div>

    </div>
  )
}