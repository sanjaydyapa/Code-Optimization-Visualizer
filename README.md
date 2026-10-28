# Compiler Optimization Visualizer

This project is a web-based educational tool for demonstrating compiler optimization passes. The frontend is built with React and the backend uses Python with Flask.

## Features

- Source code input area
- Lexical analysis view
- Syntax tree and AST summary
- Optimization passes such as:
  - Constant folding
  - Constant propagation
  - Dead code elimination
  - Common subexpression elimination
- Side-by-side original and optimized code output

## Run locally

1. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```
3. Start the backend:
   ```bash
   python backend/app.py
   ```
4. Start the frontend:
   ```bash
   cd frontend
   npm run dev -- --host 0.0.0.0
   ```
5. Open http://localhost:5173 in a browser.

## Project goal

The application aligns with the project abstract by making compiler optimization concepts interactive and easier for students to learn.
