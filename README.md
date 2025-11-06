# FishBuddy

An interactive CLI to chat with your OpenAI Assistant about fishing in Switzerland, focusing on licences, legality, and optional local weather context.  

## Features

- Interactive Q&A loop with context preserved in a single Assistant thread.  
- Optional live weather (ICON via Open‑Meteo) using latitude/longitude with no extra weather API key.  
- Canton‑aware licence scaffold acknowledging that Swiss rules vary by canton.  

## Requirements

- Python 3.9+  
- Dependencies from requirements.txt (OpenAI SDK, python‑dotenv, requests)  
- Environment variables: `OPENAI_API_KEY`, `ASSISTANT_ID`

## Setup

1) Create and activate a virtual environment (optional but recommended).  
2) Install dependencies:  

3) Configure secrets without hard‑coding:  
- Copy the example and fill your values:  
  ```
  cp .env.example .env
  ```  
- Edit `.env` and set `OPENAI_API_KEY` and `ASSISTANT_ID`.  
4) Ensure `.env` is ignored by Git; `.env.example` remains tracked so collaborators know what to set.

## Run

Recommended (package mode, from the parent directory of `fishbuddy/`):  

## Configuration

- The CLI loads `.env` at startup so secrets are not hard‑coded.  
- You can also define variables in your IDE run configuration if preferred.
