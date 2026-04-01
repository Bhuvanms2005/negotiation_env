import axios from "axios"

const API = axios.create({
  baseURL: "http://127.0.0.1:8000"
})

export const resetEnv = () => API.get("/reset")

export const stepEnv = (obs, mode, message, history) =>
  API.post("/step", {
    observation: obs,
    mode,
    user_message: message,
    history: history.map(m => m.text)
  })