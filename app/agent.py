import os
import json
import google.generativeai as genai


def rule_based_agent(obs):
    client_budget = obs["client_budget"]
    last_offer = obs.get("last_offer")
    round_num = obs.get("round", 0)

    if last_offer is None:
        return {
            "price_offer": client_budget + 2000,
            "message": "Based on the project requirements and expected quality, I propose an initial offer that ensures high-quality delivery and reliability."
        }

    if round_num == 1:
        return {
            "price_offer": last_offer - 500,
            "message": "I understand your budget concerns. I can reduce slightly while maintaining quality."
        }

    if round_num == 2:
        return {
            "price_offer": last_offer - 300,
            "message": "Trying to find a fair balance for both sides while keeping quality intact."
        }

    return {
        "price_offer": client_budget,
        "message": "Let's finalize at your budget and move forward."
    }


def safe_price_adjustment(new_price, obs):
    last_offer = obs.get("last_offer")

    if last_offer is None:
        return new_price

    if abs(new_price - last_offer) > 1500:
        return int((new_price + last_offer) / 2)

    return new_price


def gemini_agent(obs):
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-pro")

    user_message = obs.get("user_message", "")
    history = obs.get("history", [])

    history_text = "\n".join(history[-5:])

    prompt = f"""
You are an expert negotiation agent.

Conversation so far:
{history_text}

Current State:
- Client budget: {obs["client_budget"]}
- Your last offer: {obs.get("last_offer")}
- Round: {obs.get("round")}
- Client message: "{user_message}"

Your goals:
- Maximize profit but close the deal
- Move price gradually (never big jumps)
- If client gives near value → converge
- Justify your pricing with reasoning
- Be persuasive and human-like

STRICT RULES:
- Never drop price drastically
- Always consider last offer
- Respond to client message directly
- Keep negotiation realistic

Output ONLY JSON:
{{
  "price_offer": number,
  "message": "3-5 line persuasive response"
}}
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        if "```" in text:
            text = text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(text)

        price = int(parsed["price_offer"])
        price = safe_price_adjustment(price, obs)

        return {
            "price_offer": price,
            "message": parsed["message"]
        }

    except Exception as e:
        return rule_based_agent(obs)


def get_action(obs, mode="auto"):
    if mode == "rule":
        return rule_based_agent(obs)

    if mode == "gemini":
        try:
            return gemini_agent(obs)
        except:
            return rule_based_agent(obs)

    try:
        return gemini_agent(obs)
    except:
        return rule_based_agent(obs)