import React from 'react';

export default function Ai({ api, selectedCaseId, chat, setChat, transactions }) {
  const [question, setQuestion] = React.useState('');
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
    try {
      const answer = await api('/ai/chat', {
        method: 'POST',
        body: JSON.stringify({ case_id: selectedCaseId, question: text, conversation_history: next }),
      });
      setChat([...next, { role: 'assistant', content: answer.answer || answer.response || JSON.stringify(answer) }]);
    } catch (error) {
      const fallback = transactions.length
        ? `I found ${transactions.length} transaction(s) in this case. Review high-value credits/debits and run the detector suite for a stronger explanation.`
        : error.message;
      setChat([...next, { role: 'assistant', content: fallback }]);
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
      <div className="chat-window">
        {chat.length === 0 ? (
          <span className="empty-line">// Empty session. Type a question below or pick a preset.</span>
        ) : (
          chat.map((item, index) => (
            <div className={`chat-line ${item.role}`} key={`${item.role}-${index}`}>
              <strong>{item.role}</strong>
              <p>{item.content}</p>
            </div>
          ))
        )}
      </div>
      <form className="chat-form" onSubmit={(event) => { event.preventDefault(); ask(); }}>
        <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask anything about this case..." />
        <button className="dark-button" type="submit">Send</button>
      </form>
    </section>
  );
}
