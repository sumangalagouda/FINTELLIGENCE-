import React, { useState } from 'react';
import CaseList from '../components/CaseList';

export default function Ai({ api, cases, selectedCaseId, setSelectedCaseId, chat, setChat, transactions }) {
  const [pageViewMode, setPageViewMode] = useState('list');
  const [question, setQuestion] = React.useState('');
  const [isTyping, setIsTyping] = useState(false);
  const presets = [
    'Show suspicious transactions',
    'Why was this case flagged?',
    'Trace the money trail',
    'Explain this case in plain language',
  ];

  const ask = async (text = question) => {
    if (!text.trim() || !selectedCaseId) return;
    const next = [...chat, { role: 'user', content: text }];
    setChat(next);
    setQuestion('');
    setIsTyping(true);
    try {
      const answer = await api('/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: selectedCaseId, question: text, conversation_history: next }),
      });
      setChat([...next, { role: 'assistant', content: answer.answer || answer.response || JSON.stringify(answer) }]);
    } catch (error) {
      const fallback = transactions?.length
        ? `I found ${transactions.length} transaction(s) in this case. Review high-value credits/debits and run the detector suite for a stronger explanation.`
        : error.message;
      setChat([...next, { role: 'assistant', content: fallback }]);
    } finally {
      setIsTyping(false);
    }
  };

  const runAdvancedTool = async (name, path, method = 'GET') => {
    if (!selectedCaseId) return;
    const next = [...chat, { role: 'user', content: `[SYSTEM] Run ${name}` }];
    setChat(next);
    setIsTyping(true);
    try {
      const opts = { method, headers: { 'Content-Type': 'application/json' } };
      if (method === 'POST') opts.body = JSON.stringify({ case_id: selectedCaseId });
      
      const answer = await api(path, opts);
      const content = answer.patterns ? JSON.stringify(answer.patterns, null, 2) 
                    : answer.severity ? `Severity: ${answer.severity}\nScore: ${answer.score}\nFactors: ${answer.factors?.join(', ')}`
                    : answer.recommendation ? `Recommendation: ${answer.recommendation}\nConfidence: ${answer.confidence}\nReason: ${answer.reason}`
                    : JSON.stringify(answer, null, 2);
                    
      setChat([...next, { role: 'assistant', content }]);
    } catch (error) {
      setChat([...next, { role: 'assistant', content: error.message }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <section className="ai-view">

      <p className="subcopy">Powered by the backend investigator endpoint. Ask around the selected statement context.</p>
      <div className="preset-row">
        {presets.map((preset) => (
          <button key={preset} onClick={() => ask(preset)} type="button">{preset}</button>
        ))}
      </div>
      <div className="preset-row" style={{ marginTop: '8px' }}>
        <button onClick={() => runAdvancedTool('Identify Patterns', '/ai/identify-patterns', 'POST')} type="button" style={{ background: '#eef2ff', borderColor: '#c7d2fe', color: '#4f46e5' }}>Identify Patterns</button>
        <button onClick={() => runAdvancedTool('Case Severity', `/ai/case-severity/${selectedCaseId}`)} type="button" style={{ background: '#eef2ff', borderColor: '#c7d2fe', color: '#4f46e5' }}>Case Severity</button>
        <button onClick={() => runAdvancedTool('FIR Recommendation', `/intelligence/submission-recommendation/${selectedCaseId}`)} type="button" style={{ background: '#eef2ff', borderColor: '#c7d2fe', color: '#4f46e5' }}>FIR Recommendation</button>
      </div>
      <div className="chat-window">
        {chat.length === 0 ? (
          <span className="empty-line">// Empty session. Type a question below or pick a preset.</span>
        ) : (
          chat.map((item, index) => (
            <div className={`chat-line ${item.role}`} key={`${item.role}-${index}`}>
              <strong>{item.role === 'user' ? 'You' : 'AI Investigator'}</strong>
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', margin: 0 }}>{item.content}</pre>
            </div>
          ))
        )}
        {isTyping && (
          <div className="chat-line assistant">
            <strong>AI Investigator</strong>
            <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', margin: 0, color: 'var(--text-muted)' }}>Thinking...</pre>
          </div>
        )}
      </div>
      <form className="chat-form" onSubmit={(event) => { event.preventDefault(); ask(); }}>
        <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask anything about this case..." />
        <button className="dark-button" type="submit">Send</button>
      </form>
    </section>
  );
}
