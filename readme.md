# Negotiation Environment for AI Agents

## Overview

This project implements a real-world negotiation environment where an AI agent interacts with a client to reach a mutually acceptable agreement. The environment simulates realistic negotiation dynamics including counter-offers, persuasion, and deal closure.

The system supports both rule-based and LLM-driven agents, allowing evaluation of agent performance in a structured and measurable setting.

---

## Problem Motivation

Negotiation is a critical real-world task in domains such as freelancing, sales, procurement, and contract management. Most existing environments focus on games or simplified tasks, whereas this environment models a realistic human-in-the-loop negotiation process.

This project aims to provide a benchmark environment for evaluating how well AI agents can:

- Understand user intent
- Adapt pricing strategies
- Persuade and negotiate effectively
- Reach optimal agreements

---
## Live Demo

Run using Docker:

docker build -t negotiation-env .
docker run -p 8000:7860 negotiation-env


## Environment Design

### Observation Space

The environment provides the following structured observation:

- client_budget: Current client budget or counter-offer
- deadline: Project deadline constraint
- last_offer: Last price proposed by the agent
- round: Current negotiation round
- user_message: Latest client message
- history: Conversation history

---

### Action Space

The agent returns:

- price_offer: Proposed price
- message: Negotiation response

---

### Reward Function

The reward function evaluates:

- Proximity to agreement
- Profitability of the deal
- Efficiency (fewer steps preferred)

Additional reward is given when the deal is successfully closed.

---

### Episode Termination

The episode ends when:

- The client accepts the offer
- The agent and client converge within a small price range
- Maximum number of rounds is reached

---

## Tasks

The environment includes multiple negotiation scenarios with varying difficulty levels:

- Easy: Flexible client with moderate budget
- Medium: Budget-constrained client
- Hard: Strict negotiation with tight constraints

Each task includes deterministic grading logic.

---

## Agents

### Rule-Based Agent

- Uses predefined heuristics
- Provides a baseline for comparison

### Gemini-Based Agent

- Uses LLM for dynamic negotiation
- Adapts based on user input and conversation history
- Falls back to rule-based logic if API fails

---

## Frontend Interface

The system includes an interactive UI with:

- Real-time chat interface
- Reward trend visualization
- Negotiation comparison graph
- Final deal summary with score

---

## Evaluation Metrics

A negotiation score is calculated based on:

- Profitability of final agreement
- Number of negotiation steps taken

This enables benchmarking different agent strategies.

---

## Running the Project

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
Frontend
cd frontend
npm install
npm run dev

API Endpoints
GET /reset
Initializes a new negotiation episode

POST /step
Takes user input and returns next state, reward, and agent action

Environment Variables
To enable LLM agent:

GEMINI_API_KEY=your_api_key_here
If not provided, the system falls back to rule-based behavior.

Deployment
The environment is containerized and can be deployed using Docker and Hugging Face Spaces.

Key Highlights
Real-world negotiation simulation

Human-in-the-loop interaction

LLM + rule-based hybrid agent

Reward shaping and evaluation metrics

Interactive visualization dashboard

Future Improvements
Multi-agent negotiation scenarios

Personality-based agents

Advanced intent detection

Reinforcement learning training loop