import { CircularProgressbar } from "react-circular-progressbar"
import "react-circular-progressbar/dist/styles.css"

export default function SuccessGauge({ value }) {
  return (
    <div className="bg-gray-900 p-4 rounded-2xl mt-4">
      <h3 className="text-sm mb-2">Success Probability</h3>
      <CircularProgressbar value={value} text={`${value}%`} />
    </div>
  )
}