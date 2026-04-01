import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend
} from "recharts"

export default function Dashboard({ data }) {
  return (
    <div className="bg-gradient-to-br from-[#0f172a] to-[#020617] p-5 rounded-2xl h-full shadow-xl border border-gray-800 flex flex-col gap-6">

      <div>
        <h2 className="text-lg font-semibold mb-2 text-white">
          Reward Trend
        </h2>

        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="step" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="reward"
              stroke="#3b82f6"
              strokeWidth={3}
              dot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-2 text-white">
          Negotiation Comparison
        </h2>

        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="step" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip />
            <Legend />

            <Line
              type="monotone"
              dataKey="ai"
              stroke="#22c55e"
              strokeWidth={3}
              name="AI Offer"
              dot={{ r: 4 }}
            />

            <Line
              type="monotone"
              dataKey="client"
              stroke="#f59e0b"
              strokeWidth={3}
              name="Client Budget"
              dot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

    </div>
  )
}