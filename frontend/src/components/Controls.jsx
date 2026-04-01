export default function Controls({ onStart }) {
  return (
    <div className="flex gap-4 mt-4">
      <button onClick={onStart} className="bg-blue-600 px-4 py-2 rounded-xl">
        Start Simulation
      </button>
    </div>
  )
}