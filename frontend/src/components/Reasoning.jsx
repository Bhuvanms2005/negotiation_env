export default function Reasoning({ text }) {
  return (
    <div className="bg-gray-900 p-4 rounded-xl mt-4">
      <h3 className="text-sm mb-2">AI Reasoning</h3>
      <p className="text-gray-300 text-sm">{text}</p>
    </div>
  )
}