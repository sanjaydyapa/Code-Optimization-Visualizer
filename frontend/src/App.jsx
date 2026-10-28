import React, { useState } from 'react';

const defaultCode = `x = 2 + 3
result = x * 4
unused = 99
final = result + 7
repeated = x + 3
duplicate = x + 3
keep = final + repeated`;

const optimizationOptions = [
  { id: 'constant_folding', label: 'Constant Folding' },
  { id: 'constant_propagation', label: 'Constant Propagation' },
  { id: 'dead_code_elimination', label: 'Dead Code Elimination' },
  { id: 'common_subexpression_elimination', label: 'Common Subexpression Elimination' },
];

export default function App() {
  const [source, setSource] = useState(defaultCode);
  const [selected, setSelected] = useState(optimizationOptions.map((option) => option.id));
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const toggleOption = (id) => {
    setSelected((current) =>
      current.includes(id) ? current.filter((entry) => entry !== id) : [...current, id]
    );
  };

  const analyzeCode = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ source, optimizations: selected }),
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({
        summary: 'The backend is not running. Start the Python server first.',
        steps: ['Backend unavailable'],
        lexical_tokens: [],
        ast_summary: [],
        syntax_tree: '',
        pipeline: [],
        original_code: source,
        optimized_code: source,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="header">
        <div>
          <p className="eyebrow">Compiler Design Course Project</p>
          <h1>Compiler Optimization Visualizer</h1>
        </div>
      </header>

      <main className="layout">
        <section className="panel controls-panel">
          <h2>Code Input</h2>

          <textarea
            value={source}
            onChange={(event) => setSource(event.target.value)}
            spellCheck={false}
            placeholder="Enter source code..."
          />

          <div className="input-group">
            <label>Optimization passes</label>
            <div className="option-list">
              {optimizationOptions.map((option) => (
                <label key={option.id} className="option-item">
                  <input
                    type="checkbox"
                    checked={selected.includes(option.id)}
                    onChange={() => toggleOption(option.id)}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </div>

          <button className="primary-button" onClick={analyzeCode} disabled={loading}>
            {loading ? 'Analyzing...' : 'Analyze and Optimize'}
          </button>
        </section>

        {result && (
          <>
            <section className="panel result-panel">
              <h2>Optimization Result</h2>
              <p className="summary">{result.summary}</p>

              <div className="code-grid">
                <div className="code-card">
                  <h3>Original Code</h3>
                  <pre>{result.original_code}</pre>
                </div>
                <div className="code-card">
                  <h3>Optimized Code</h3>
                  <pre>{result.optimized_code}</pre>
                </div>
              </div>
            </section>

            <section className="panel details-panel">
              <h2>Pipeline View</h2>
              <div className="pipeline-list">
                {result.pipeline.map((step) => (
                  <div key={step.name} className="pipeline-step">
                    <strong>{step.name}</strong>
                    <span>{step.value}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel details-panel">
              <h2>Analysis Details</h2>
              <div className="detail-grid">
                <div>
                  <h3>Lexical Tokens</h3>
                  <div className="chip-list">
                    {result.lexical_tokens.map((token, index) => (
                      <span key={`${token}-${index}`} className="chip">
                        {token}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <h3>AST Summary</h3>
                  <div className="chip-list">
                    {result.ast_summary.map((node, index) => (
                      <span key={`${node}-${index}`} className="chip accent">
                        {node}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="steps-box">
                <h3>Transformation Notes</h3>
                <ul>
                  {result.steps.length > 0 ? (
                    result.steps.map((step, index) => <li key={`${step}-${index}`}>{step}</li>)
                  ) : (
                    <li>No transformations were applied.</li>
                  )}
                </ul>
              </div>

              <div className="syntax-box">
                <h3>Syntax Tree</h3>
                <pre>{result.syntax_tree}</pre>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
